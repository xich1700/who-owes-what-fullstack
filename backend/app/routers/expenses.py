from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_manager, get_owned_group
from ..logic import compute_totals, simplify_debts
from ..nlp import parse_expense_sentence
from ..receipt import extract_receipt_via_ai

router = APIRouter(tags=["expenses"])


def _expense_to_out(e: models.Expense) -> schemas.ExpenseOut:
    return schemas.ExpenseOut(
        id=e.id,
        payer_id=e.payer_id,
        amount=e.amount,
        label=e.label or "",
        is_recurring=e.is_recurring,
        beneficiaries={b.person_id: b.weight for b in e.beneficiaries},
    )


@router.get("/groups/{group_id}/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group.id).all()
    return [_expense_to_out(e) for e in expenses]


@router.post("/groups/{group_id}/expenses", response_model=schemas.ExpenseOut)
def add_expense(
    group_id: str,
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")
    if not payload.beneficiary_weights:
        raise HTTPException(status_code=400, detail="You need at least one beneficiary.")

    valid_ids = {p.id for p in db.query(models.Person).filter(models.Person.group_id == group.id).all()}
    if payload.payer_id not in valid_ids:
        raise HTTPException(status_code=400, detail="Payer is not in this group.")
    if not set(payload.beneficiary_weights.keys()).issubset(valid_ids):
        raise HTTPException(status_code=400, detail="One or more beneficiaries are not in this group.")

    expense = models.Expense(
        group_id=group.id,
        payer_id=payload.payer_id,
        amount=payload.amount,
        label=payload.label.strip(),
        is_recurring=payload.is_recurring,
    )
    db.add(expense)
    db.flush()  # get expense.id before inserting children

    for pid, weight in payload.beneficiary_weights.items():
        db.add(models.ExpenseBeneficiary(expense_id=expense.id, person_id=pid, weight=weight))

    db.commit()
    db.refresh(expense)
    return _expense_to_out(expense)


@router.put("/groups/{group_id}/expenses/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    group_id: str,
    expense_id: str,
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")

    expense = db.query(models.Expense).filter(
        models.Expense.id == expense_id, models.Expense.group_id == group.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found.")

    expense.payer_id = payload.payer_id
    expense.amount = payload.amount
    expense.label = payload.label.strip()
    expense.is_recurring = payload.is_recurring

    db.query(models.ExpenseBeneficiary).filter(models.ExpenseBeneficiary.expense_id == expense.id).delete()
    for pid, weight in payload.beneficiary_weights.items():
        db.add(models.ExpenseBeneficiary(expense_id=expense.id, person_id=pid, weight=weight))

    db.commit()
    db.refresh(expense)
    return _expense_to_out(expense)


@router.delete("/groups/{group_id}/expenses/{expense_id}")
def delete_expense(
    group_id: str,
    expense_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")

    expense = db.query(models.Expense).filter(
        models.Expense.id == expense_id, models.Expense.group_id == group.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found.")

    db.delete(expense)
    db.commit()
    return {"detail": "Expense deleted."}


@router.post("/groups/{group_id}/expenses/{expense_id}/repeat", response_model=schemas.ExpenseOut)
def repeat_expense(
    group_id: str,
    expense_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    """Duplicates a recurring expense as a new expense logged right now."""
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")

    source = db.query(models.Expense).filter(
        models.Expense.id == expense_id, models.Expense.group_id == group.id
    ).first()
    if source is None:
        raise HTTPException(status_code=404, detail="Expense not found.")

    new_expense = models.Expense(
        group_id=group.id, payer_id=source.payer_id, amount=source.amount,
        label=source.label, is_recurring=True,
    )
    db.add(new_expense)
    db.flush()
    for b in source.beneficiaries:
        db.add(models.ExpenseBeneficiary(expense_id=new_expense.id, person_id=b.person_id, weight=b.weight))
    db.commit()
    db.refresh(new_expense)
    return _expense_to_out(new_expense)


# ---- Natural-language parsing (never auto-saves - caller must confirm via add_expense) ----
@router.post("/groups/{group_id}/expenses/parse", response_model=schemas.ParseExpenseResult)
def parse_expense(
    group_id: str,
    payload: schemas.ParseExpenseRequest,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    people = db.query(models.Person).filter(models.Person.group_id == group.id).all()
    people_dicts = [{"id": p.id, "name": p.name} for p in people]
    result = parse_expense_sentence(payload.sentence, people_dicts)
    return schemas.ParseExpenseResult(**result)


# ---- Receipt scanning (never auto-saves - same rule as NLP parsing above) ----
@router.post("/groups/{group_id}/expenses/scan-receipt", response_model=schemas.ScanReceiptResult)
def scan_receipt(
    group_id: str,
    api_key: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    get_owned_group(group_id, db, manager)  # just verifies ownership; group itself unused here

    if not api_key.strip():
        raise HTTPException(status_code=400, detail="Enter your Anthropic API key.")
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Please upload a JPEG or PNG photo.")

    image_bytes = file.file.read()
    media_type = "image/png" if file.content_type == "image/png" else "image/jpeg"

    result, error = extract_receipt_via_ai(image_bytes, media_type, api_key.strip())
    if error:
        raise HTTPException(status_code=400, detail=error)
    return schemas.ScanReceiptResult(**result)


# ---- Repayments ----
@router.get("/groups/{group_id}/repayments", response_model=list[schemas.RepaymentOut])
def list_repayments(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    return db.query(models.Repayment).filter(models.Repayment.group_id == group.id).all()


@router.post("/groups/{group_id}/repayments", response_model=schemas.RepaymentOut)
def add_repayment(
    group_id: str,
    payload: schemas.RepaymentCreate,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")
    if payload.from_person_id == payload.to_person_id:
        raise HTTPException(status_code=400, detail="Pick two different people.")

    repayment = models.Repayment(
        group_id=group.id, from_person_id=payload.from_person_id,
        to_person_id=payload.to_person_id, amount=payload.amount,
    )
    db.add(repayment)
    db.commit()
    db.refresh(repayment)
    return repayment


@router.delete("/groups/{group_id}/repayments/{repayment_id}")
def delete_repayment(
    group_id: str,
    repayment_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")

    repayment = db.query(models.Repayment).filter(
        models.Repayment.id == repayment_id, models.Repayment.group_id == group.id
    ).first()
    if repayment is None:
        raise HTTPException(status_code=404, detail="Repayment not found.")

    db.delete(repayment)
    db.commit()
    return {"detail": "Repayment undone."}


# ---- Totals ----
@router.get("/groups/{group_id}/totals", response_model=schemas.TotalsOut)
def get_totals(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    people = db.query(models.Person).filter(models.Person.group_id == group.id).all()
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group.id).all()
    repayments = db.query(models.Repayment).filter(models.Repayment.group_id == group.id).all()

    expense_dicts = [
        {"payer_id": e.payer_id, "amount": e.amount, "beneficiaries": {b.person_id: b.weight for b in e.beneficiaries}}
        for e in expenses
    ]
    repayment_dicts = [
        {"from_person_id": r.from_person_id, "to_person_id": r.to_person_id, "amount": r.amount}
        for r in repayments
    ]
    name_by_id = {p.id: p.name for p in people}
    paid, share, expense_balance, outstanding, total_spent = compute_totals(
        [p.id for p in people], expense_dicts, repayment_dicts
    )
    plan = simplify_debts(outstanding, name_by_id)

    balances = [
        schemas.PersonBalance(
            person_id=p.id, name=p.name, paid=paid[p.id], share=share[p.id], outstanding=outstanding[p.id],
        )
        for p in people
    ]
    transactions = [schemas.SettlementTransaction(**t) for t in plan]

    return schemas.TotalsOut(
        total_spent=total_spent, currency=group.currency, balances=balances, settlement_plan=transactions,
    )
