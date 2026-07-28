import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_manager, get_owned_group

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[schemas.GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    return db.query(models.Group).filter(models.Group.manager_id == manager.id).order_by(models.Group.name).all()


@router.post("", response_model=schemas.GroupOut)
def create_group(
    payload: schemas.GroupCreate,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    existing = db.query(models.Group).filter(
        models.Group.manager_id == manager.id,
        models.Group.name.ilike(payload.name),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a group with this name.")

    group = models.Group(
        manager_id=manager.id,
        name=payload.name,
        currency=payload.currency,
        share_token=secrets.token_urlsafe(10),
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=schemas.GroupOut)
def get_group(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    return get_owned_group(group_id, db, manager)


@router.delete("/{group_id}")
def delete_group(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    db.delete(group)  # cascades to people/expenses/beneficiaries/repayments
    db.commit()
    return {"detail": "Group deleted."}


@router.post("/{group_id}/close", response_model=schemas.GroupOut)
def close_group(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    from ..logic import compute_totals

    group = get_owned_group(group_id, db, manager)
    people = db.query(models.Person).filter(models.Person.group_id == group.id).all()
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group.id).all()
    repayments = db.query(models.Repayment).filter(models.Repayment.group_id == group.id).all()

    expense_dicts = [
        {
            "payer_id": e.payer_id,
            "amount": e.amount,
            "beneficiaries": {b.person_id: b.weight for b in e.beneficiaries},
        }
        for e in expenses
    ]
    repayment_dicts = [
        {"from_person_id": r.from_person_id, "to_person_id": r.to_person_id, "amount": r.amount}
        for r in repayments
    ]
    _, _, _, outstanding, _ = compute_totals([p.id for p in people], expense_dicts, repayment_dicts)

    if not all(abs(v) < 0.005 for v in outstanding.values()):
        raise HTTPException(status_code=400, detail="Balances must all be zero before this group can be closed.")

    group.closed = True
    db.commit()
    db.refresh(group)
    return group


# ---- People ----
@router.get("/{group_id}/people", response_model=list[schemas.PersonOut])
def list_people(
    group_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    return db.query(models.Person).filter(models.Person.group_id == group.id).order_by(models.Person.name).all()


@router.post("/{group_id}/people", response_model=schemas.PersonOut)
def add_person(
    group_id: str,
    payload: schemas.PersonCreate,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")

    existing = db.query(models.Person).filter(
        models.Person.group_id == group.id,
        models.Person.name.ilike(payload.name),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{payload.name}' is already in the group.")

    person = models.Person(group_id=group.id, name=payload.name)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.delete("/{group_id}/people/{person_id}")
def remove_person(
    group_id: str,
    person_id: str,
    db: Session = Depends(get_db),
    manager: models.Manager = Depends(get_current_manager),
):
    group = get_owned_group(group_id, db, manager)
    if group.closed:
        raise HTTPException(status_code=400, detail="This group is closed.")

    person = db.query(models.Person).filter(
        models.Person.id == person_id, models.Person.group_id == group.id
    ).first()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    in_expenses = (
        db.query(models.Expense).filter(models.Expense.payer_id == person.id).first()
        or db.query(models.ExpenseBeneficiary).filter(models.ExpenseBeneficiary.person_id == person.id).first()
    )
    if in_expenses:
        raise HTTPException(
            status_code=400,
            detail="This person appears in at least one expense and can't be removed. Edit or delete those expenses first.",
        )

    db.delete(person)
    db.commit()
    return {"detail": "Person removed."}
