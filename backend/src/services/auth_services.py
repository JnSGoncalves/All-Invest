"""
Placeholder de autenticação — dependencies/auth.py

Hoje retorna um usuário mockado para destravar o desenvolvimento dos
endpoints. A assinatura já está no formato final, então quando o OAuth 2.0
entrar, só o corpo da função muda — nenhum router precisa ser alterado.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..db import schemas
from ..db.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

# Usuário fixo enquanto a autenticação não está implementada
MOCK_USER = schemas.UserOut(
    user_id=1,
    name="Usuário Mock",
    email="mock@exemplo.com",
    created_at="2026-01-01T00:00:00+00:00",
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> schemas.UserOut:
    """
    Resolve o usuário autenticado a partir do token OAuth 2.0.

    TODO (quando o OAuth entrar):
      1. Decodificar o JWT (python-jose / PyJWT) validando assinatura e exp.
      2. Extrair o `sub` (user_id) das claims.
      3. Buscar o usuário: crud.get_user(db, user_id).
      4. Levantar 401 se token ausente, inválido, expirado ou usuário inexistente.
    """
    # --- comportamento temporário ---
    return MOCK_USER

    # --- implementação futura ---
    # if not token:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Não autenticado.",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    # payload = decode_token(token)
    # user = crud.get_user(db, int(payload["sub"]))
    # if not user:
    #     raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.")
    # return user


def verify_api_key(api_key: str, db: Session) -> bool:
    """
    Validação da chave de aplicativo (tabela `api_keys`).

    Distinta do OAuth: identifica o *aplicativo* cliente, não o usuário.
    Uso típico: header `X-API-Key` validado em conjunto com o Bearer token.
    """
    # TODO: consultar api_keys e comparar hash da chave recebida
    raise NotImplementedError