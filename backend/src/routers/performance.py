from typing import Annotated

from fastapi import APIRouter, Depends, Path

from ..db import schemas
from ..dependencies.auth import CurrentUser, get_current_user
from ..dependencies.components import get_performance_service
from ..interfaces import IPerformanceService

router = APIRouter(
    prefix="/api/performance",
    tags=["performance"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Autenticação ou chave de API inválida."},
        404: {
            "description": "Carteira inexistente, pertencente a outro usuário ou cotação não encontrada."
        },
        504: {"description": "Tempo de consulta excedido."},
    },
)

PortfolioId = Annotated[int, Path(gt=0, description="Identificador da carteira.")]


@router.get(
    "/portfolios/{portfolio_id}/positions",
    response_model=list[schemas.PositionValuationOut],
)
async def avaliar_posicoes(
    portfolio_id: PortfolioId,
    current_user: CurrentUser,
    performance: IPerformanceService = Depends(get_performance_service),
):
    """avaliarPosicoes - Posições da carteira avaliadas com as cotações atuais."""
    return await performance.evaluate_positions(current_user.user_id, portfolio_id)


@router.get(
    "/portfolios/{portfolio_id}/positions/{stock_name}",
    response_model=schemas.StockPerformanceOut,
)
async def consultar_desempenho_acao(
    portfolio_id: PortfolioId,
    stock_name: str,
    current_user: CurrentUser,
    performance: IPerformanceService = Depends(get_performance_service),
):
    """consultarDesempenhoAcao - Resultado de uma ação da carteira."""
    return await performance.get_stock_performance(
        current_user.user_id, portfolio_id, stock_name
    )


@router.get("/portfolios/{portfolio_id}", response_model=schemas.PortfolioPerformanceOut)
async def obter_desempenho_carteira(
    portfolio_id: PortfolioId,
    current_user: CurrentUser,
    performance: IPerformanceService = Depends(get_performance_service),
):
    """obterDesempenhoCarteira - Totais, rentabilidade e detalhamento por ação."""
    return await performance.get_portfolio_performance(current_user.user_id, portfolio_id)
