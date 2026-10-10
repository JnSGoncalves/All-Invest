from fastapi import APIRouter, Depends, HTTPException, status

from ..db import schemas
from ..dependencies.components import get_user_service
from ..interfaces import IUserService

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(
    user_in: schemas.UserCreate,
    users: IUserService = Depends(get_user_service),
):
    """
    HU01 - Cadastro de usuário.

    CA01 (Cadastro): dados válidos e e-mail novo -> salva e retorna 201.
    CA02 (Conta Existente): e-mail já cadastrado -> retorna 409 com mensagem clara.
    """
    if users.get_by_email(str(user_in.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta cadastrada com este e-mail.",
        )

    return users.create(user_in)
