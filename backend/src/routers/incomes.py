from fastapi import APIRouter, Depends, Response

from ..db import schemas
from ..dependencies.auth import CurrentUser
from ..interfaces.components import IIncomeService
from ..dependencies.components import get_income_service

router = APIRouter(prefix="/api/incomes", tags=["incomes"])


@router.get("", response_model=list[schemas.IncomeOut])
def listar_rendimentos(user: CurrentUser, service: IIncomeService = Depends(get_income_service)):
    return service.list(user.user_id)


@router.post("", response_model=schemas.IncomeOut, status_code=201)
def cadastrar_rendimento(payload: schemas.IncomeCreate, user: CurrentUser,
                         service: IIncomeService = Depends(get_income_service)):
    return service.save(user.user_id, payload)


@router.put("/{income_id}", response_model=schemas.IncomeOut)
def editar_rendimento(income_id: int, payload: schemas.IncomeCreate, user: CurrentUser,
                      service: IIncomeService = Depends(get_income_service)):
    return service.save(user.user_id, payload, income_id)


@router.delete("/{income_id}", status_code=204)
def remover_rendimento(income_id: int, user: CurrentUser,
                       service: IIncomeService = Depends(get_income_service)):
    service.delete(user.user_id, income_id)
    return Response(status_code=204)
