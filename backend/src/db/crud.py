import secrets
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..services import security
from .. import models
from . import schemas


def validate_api_key(db: Session, api_key: str) -> bool:
    return (
        db.query(models.ApiKey)
        .filter(models.ApiKey.api_key == api_key)
        .first()
        is not None
    )
    

def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return (
        db.query(models.User)
        .filter(models.User.email == email.strip().lower())
        .first()
    )


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """Persistência do Usuário (CA01): cria o registro com a senha já hasheada."""
    db_user = models.User(
        name=user_in.name.strip(),
        email=str(user_in.email).strip().lower(),
        password_hash=security.hash_password(user_in.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_google_user(db: Session, name: str, email: str) -> models.User:
    """Cria um usuário autenticado pelo Google sem armazenar senha utilizável."""
    db_user = models.User(
        name=name.strip(),
        email=email.strip().lower(),
        password_hash=security.hash_password(secrets.token_urlsafe(32)),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def add_refresh_token(
    db: Session,
    *,
    user_id: int,
    token_hash: str,
    expire_at: datetime,
) -> models.RefreshToken:
    token = models.RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expire_at=expire_at,
    )
    db.add(token)
    return token


def get_refresh_token_for_update(
    db: Session,
    token_hash: str,
) -> models.RefreshToken | None:
    return (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first()
    )


def revoke_refresh_token(db: Session, *, token_hash: str, user_id: int) -> bool:
    result = db.execute(
        delete(models.RefreshToken).where(
            models.RefreshToken.token_hash == token_hash,
            models.RefreshToken.user_id == user_id,
        )
    )
    db.commit()
    return bool(result.rowcount)


def revoke_all_refresh_tokens(db: Session, user_id: int) -> int:
    result = db.execute(
        delete(models.RefreshToken).where(models.RefreshToken.user_id == user_id)
    )
    db.commit()
    return int(result.rowcount or 0)
