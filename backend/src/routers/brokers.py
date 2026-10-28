from fastapi import APIRouter, Depends, status

from ..db import schemas
from ..dependencies.auth import get_current_user
from ..dependencies.components import get_broker_service
from ..interfaces import IBrokerService

router = APIRouter(
    prefix="/api/brokers",
    tags=["brokers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.BrokerOut])
def listar_corretoras(brokers: IBrokerService = Depends(get_broker_service)):
    """Lista o catálogo global de corretoras, em ordem alfabética."""
    return brokers.list_brokers()


@router.post("", response_model=schemas.BrokerOut, status_code=status.HTTP_201_CREATED)
def cadastrar_corretora(
    broker_in: schemas.BrokerCreate,
    brokers: IBrokerService = Depends(get_broker_service),
):
    """Cadastra uma corretora no catálogo, disponível para todos os usuários."""
    return brokers.create_broker(broker_in)


@router.delete("/{broker_id}", response_model=schemas.MessageResponse)
def remover_corretora(
    broker_id: int,
    brokers: IBrokerService = Depends(get_broker_service),
):
    """Remove a corretora, desde que nenhuma operação a utilize."""
    brokers.delete_broker(broker_id)
    return schemas.MessageResponse(message="Corretora removida.")
