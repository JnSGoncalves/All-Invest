from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, security
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    HU02 - Login do usuário.

    CA01 (Login): credenciais corretas -> autentica e retorna um token de sessão.
    CA02 (Conta inexistente): e-mail não cadastrado -> avisa e sugere o cadastro.
    Senha incorreta (conta existe): 401, sem revelar detalhes além do necessário.
    """
    user = crud.get_user_by_email(db, credentials.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos uma conta com este e-mail. Que tal se cadastrar?",
        )

    if not security.verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    access_token = security.create_access_token(user.user_id)
    return schemas.Token(access_token=access_token)
