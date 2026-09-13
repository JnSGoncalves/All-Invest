from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import schemas
from ..db import crud
from ..db.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    HU01 - Cadastro de usuário.

    CA01 (Cadastro): dados válidos e e-mail novo -> salva e retorna 201.
    CA02 (Conta Existente): e-mail já cadastrado -> retorna 409 com mensagem clara.
    """
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta cadastrada com este e-mail.",
        )

    return crud.create_user(db, user_in)
