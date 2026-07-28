from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .auth import decode_access_token
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_manager(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Manager:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    manager_id = decode_access_token(token)
    if manager_id is None:
        raise credentials_error
    manager = db.query(models.Manager).filter(models.Manager.id == manager_id).first()
    if manager is None:
        raise credentials_error
    return manager


def get_owned_group(group_id: str, db: Session, manager: models.Manager) -> models.Group:
    """Fetches a group and verifies the current manager owns it - raises 404 otherwise
    (404, not 403, so we don't leak whether a group ID exists to a non-owner)."""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if group is None or group.manager_id != manager.id:
        raise HTTPException(status_code=404, detail="Group not found")
    return group
