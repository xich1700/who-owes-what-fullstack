from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_access_token
from ..database import get_db
from ..logic import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalized(s: str) -> str:
    return s.strip().lower()


@router.post("/signup", response_model=schemas.TokenResponse)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.Manager).filter(
        models.Manager.username.ilike(payload.username)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This username is already taken.")

    salt, pwd_hash = hash_password(payload.password)
    ans_salt, ans_hash = hash_password(_normalized(payload.security_answer))

    manager = models.Manager(
        username=payload.username,
        salt=salt,
        password_hash=pwd_hash,
        security_question=payload.security_question,
        security_answer_salt=ans_salt,
        security_answer_hash=ans_hash,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)

    token = create_access_token(manager.id)
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    manager = db.query(models.Manager).filter(
        models.Manager.username.ilike(payload.username)
    ).first()
    if manager is None or not verify_password(payload.password, manager.salt, manager.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    token = create_access_token(manager.id)
    return schemas.TokenResponse(access_token=token)


@router.post("/forgot-password/lookup")
def forgot_password_lookup(payload: schemas.ForgotPasswordLookup, db: Session = Depends(get_db)):
    manager = db.query(models.Manager).filter(
        models.Manager.username.ilike(payload.username)
    ).first()
    if manager is None:
        raise HTTPException(status_code=404, detail="No account with this username.")
    if not manager.security_question:
        raise HTTPException(
            status_code=400,
            detail="This account has no security question on file.",
        )
    return {"security_question": manager.security_question}


@router.post("/forgot-password/reset")
def forgot_password_reset(payload: schemas.ForgotPasswordReset, db: Session = Depends(get_db)):
    manager = db.query(models.Manager).filter(
        models.Manager.username.ilike(payload.username)
    ).first()
    if manager is None:
        raise HTTPException(status_code=404, detail="No account with this username.")
    if not manager.security_answer_hash:
        raise HTTPException(status_code=400, detail="This account has no security answer on file.")
    if not verify_password(_normalized(payload.security_answer), manager.security_answer_salt, manager.security_answer_hash):
        raise HTTPException(status_code=400, detail="That answer doesn't match what's on file.")

    salt, pwd_hash = hash_password(payload.new_password)
    manager.salt = salt
    manager.password_hash = pwd_hash
    db.commit()
    return {"detail": "Password reset successfully."}
