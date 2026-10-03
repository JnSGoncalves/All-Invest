from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .. import models
from ..interfaces import IUserService
from ..services import security
from .components import get_user_service

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="Access token JWT retornado pelo login ou pelo refresh.",
    auto_error=False,
)


def _unauthorized(detail: str = "Autenticação necessária.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[IUserService, Depends(get_user_service)],
) -> models.User:
    """Dependência genérica para qualquer endpoint que exija usuário logado."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        user_id = security.decode_access_token(credentials.credentials)
    except security.ExpiredAccessTokenError as exc:
        raise _unauthorized("Access token expirado.") from exc
    except security.InvalidAccessTokenError as exc:
        raise _unauthorized("Access token inválido.") from exc

    user = users.get_by_id(user_id)
    if not user:
        raise _unauthorized("Usuário do token não existe.")
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
