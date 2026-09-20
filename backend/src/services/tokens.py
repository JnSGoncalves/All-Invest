from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas
from . import security


class InvalidRefreshTokenError(Exception):
    pass


def _build_auth_response(
    db: Session,
    user: models.User,
    raw_refresh_token: str,
) -> schemas.AuthResponse:
    crud.add_refresh_token(
        db,
        user_id=user.user_id,
        token_hash=security.hash_refresh_token(raw_refresh_token),
        expire_at=security.refresh_token_expiration(),
    )
    return schemas.AuthResponse(
        access_token=security.create_access_token(user.user_id),
        refresh_token=raw_refresh_token,
        expires_in=security.access_token_expires_in_seconds(),
        user=schemas.UserOut.model_validate(user),
    )


def issue_token_pair(db: Session, user: models.User) -> schemas.AuthResponse:
    response = _build_auth_response(db, user, security.generate_refresh_token())
    db.commit()
    return response


def rotate_refresh_token(db: Session, raw_refresh_token: str) -> schemas.AuthResponse:
    token_hash = security.hash_refresh_token(raw_refresh_token)
    stored_token = crud.get_refresh_token_for_update(db, token_hash)

    if not stored_token:
        raise InvalidRefreshTokenError

    if stored_token.expire_at <= security.utc_now():
        db.delete(stored_token)
        db.commit()
        raise InvalidRefreshTokenError

    user = crud.get_user_by_id(db, stored_token.user_id)
    if not user:
        db.delete(stored_token)
        db.commit()
        raise InvalidRefreshTokenError

    db.delete(stored_token)
    response = _build_auth_response(db, user, security.generate_refresh_token())
    db.commit()
    return response
