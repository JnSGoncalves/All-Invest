"""Implementação do componente de autenticação."""

from sqlalchemy.orm import Session

from .. import models
from ..db import crud
from ..interfaces import IUserService
from ..services import security, tokens
from ..db.schemas import AuthResponse


class AccountNotFoundError(Exception):
    """Não existe conta associada ao endereço informado."""


class IncorrectPasswordError(Exception):
    """A conta existe, mas a senha está incorreta."""


class InvalidRefreshSessionError(Exception):
    """Refresh token ausente, expirado ou revogado."""


class AuthService:
    def __init__(self, db: Session, users: IUserService) -> None:
        self._db = db
        self._users = users

    def authenticate(self, email: str, password: str) -> AuthResponse:
        user = self._users.get_by_email(email)
        if user is None:
            raise AccountNotFoundError
        if not security.verify_password(password, user.password_hash):
            raise IncorrectPasswordError
        return self.issue_session(user)

    def issue_session(self, user: models.User) -> AuthResponse:
        return tokens.issue_token_pair(self._db, user)

    def refresh_session(self, raw_refresh_token: str) -> AuthResponse:
        try:
            return tokens.rotate_refresh_token(self._db, raw_refresh_token)
        except tokens.InvalidRefreshTokenError as exc:
            raise InvalidRefreshSessionError from exc

    def logout(self, refresh_token: str, user_id: int) -> None:
        crud.revoke_refresh_token(
            self._db,
            token_hash=security.hash_refresh_token(refresh_token),
            user_id=user_id,
        )

    def logout_all(self, user_id: int) -> None:
        crud.revoke_all_refresh_tokens(self._db, user_id)
