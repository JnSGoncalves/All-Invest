from fastapi import APIRouter, Depends, status

from ..db import schemas
from ..dependencies.auth import CurrentUser, get_current_user
from ..dependencies.components import get_broker_service
from ..interfaces import IBrokerService

router = APIRouter(
    prefix="/api/brokers",
    tags=["brokers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.BrokerOut])
def listar_corretoras(
    current_user: CurrentUser,
    brokers: IBrokerService = Depends(get_broker_service),
):
    """HU04: lista somente as corretoras vinculadas ao usuário autenticado."""
    return brokers.list_user_brokers(current_user.user_id)


@router.get("/catalogo", response_model=list[schemas.BrokerOut])
def listar_catalogo(brokers: IBrokerService = Depends(get_broker_service)):
    """Lista o catálogo global de corretoras, em ordem alfabética."""
    return brokers.list_brokers()


@router.post("", response_model=schemas.BrokerOut, status_code=status.HTTP_201_CREATED)
def cadastrar_corretora(
    broker_in: schemas.BrokerCreate,
    current_user: CurrentUser,
    brokers: IBrokerService = Depends(get_broker_service),
):
    """Cadastra a corretora no catálogo, se preciso, e a vincula ao usuário."""
    return brokers.create_broker(current_user.user_id, broker_in)


@router.delete("/{broker_id}", response_model=schemas.MessageResponse)
def remover_corretora(
    broker_id: int,
    brokers: IBrokerService = Depends(get_broker_service),
):
    """Remove a corretora, desde que nenhuma operação a utilize."""
    brokers.delete_broker(broker_id)
    return schemas.MessageResponse(message="Corretora removida.")
