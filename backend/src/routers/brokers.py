from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import crud, schemas
from ..db.database import get_db
from ..dependencies.auth import CurrentUser
from ..interfaces.components import IBrokerService
from ..dependencies.components import get_broker_service

router = APIRouter(prefix="/api/brokers", tags=["brokers"])


@router.post("", response_model=schemas.BrokerOut, status_code=201)
def cadastrar_corretora(payload: schemas.BrokerCreate, current_user: CurrentUser,
                       service: IBrokerService = Depends(get_broker_service)):
    return service.create(current_user.user_id, payload)


@router.get("", response_model=list[schemas.BrokerOut])
def listar_corretoras(current_user: CurrentUser, db: Session = Depends(get_db)):
    """HU04: lista somente as corretoras vinculadas ao usuário autenticado."""
    return crud.list_user_brokers(db, current_user.user_id)
