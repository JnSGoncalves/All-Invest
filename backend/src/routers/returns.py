from fastapi import APIRouter, Depends, Query

from ..db import schemas
from ..dependencies.auth import CurrentUser, get_current_user
from ..dependencies.components import get_returns_service
from ..interfaces import IReturnsService

router = APIRouter(
    prefix="/api/rendimentos",
    tags=["rendimentos"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=schemas.ReturnsOut)
async def consultar_rendimento(
    current_user: CurrentUser,
    periodo: schemas.ReturnPeriod = Query(
        "1mo",
        description="1w (7 dias), 1mo (30 dias), 3mo (90 dias) ou max (desde a primeira compra).",
    ),
    portfolio_id: int | None = Query(None, gt=0, description="Restringe a uma carteira."),
    returns: IReturnsService = Depends(get_returns_service),
):
    """HU08 - Ganho ou perda dos ativos do usuário no período selecionado."""
    return await returns.get_returns(current_user.user_id, periodo, portfolio_id)
