from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..logic import compute_totals, simplify_debts

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{share_token}", response_model=schemas.GroupOut)
def get_shared_group(share_token: str, db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.share_token == share_token).first()
    if group is None:
        raise HTTPException(status_code=404, detail="This link doesn't match any group.")
    return group


@router.get("/{share_token}/people", response_model=list[schemas.PersonOut])
def get_shared_people(share_token: str, db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.share_token == share_token).first()
    if group is None:
        raise HTTPException(status_code=404, detail="This link doesn't match any group.")
    return db.query(models.Person).filter(models.Person.group_id == group.id).order_by(models.Person.name).all()


@router.get("/{share_token}/expenses")
def get_shared_expenses(share_token: str, db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.share_token == share_token).first()
    if group is None:
        raise HTTPException(status_code=404, detail="This link doesn't match any group.")
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group.id).all()
    return [
        {
            "id": e.id, "payer_id": e.payer_id, "amount": e.amount, "label": e.label or "",
            "is_recurring": e.is_recurring, "beneficiaries": {b.person_id: b.weight for b in e.beneficiaries},
        }
        for e in expenses
    ]


@router.get("/{share_token}/totals", response_model=schemas.TotalsOut)
def get_shared_totals(share_token: str, db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.share_token == share_token).first()
    if group is None:
        raise HTTPException(status_code=404, detail="This link doesn't match any group.")

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
        schemas.PersonBalance(person_id=p.id, name=p.name, paid=paid[p.id], share=share[p.id], outstanding=outstanding[p.id])
        for p in people
    ]
    transactions = [schemas.SettlementTransaction(**t) for t in plan]

    return schemas.TotalsOut(
        total_spent=total_spent, currency=group.currency, balances=balances, settlement_plan=transactions,
    )
