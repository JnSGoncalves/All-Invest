"""Compatibilidade para imports antigos do serviço de autenticação.

A autenticação é implementada em ``dependencies.auth`` e usa o JWT emitido
pelas rotas de login; este módulo não mantém usuário ou token mockado.
"""

from sqlalchemy.orm import Session

from ..db.crud import validate_api_key
from ..dependencies.auth import get_current_user


def verify_api_key(api_key: str, db: Session) -> bool:
    """Valida a chave de aplicativo persistida no banco."""
    return validate_api_key(db, api_key)
