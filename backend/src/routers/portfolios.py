from fastapi import APIRouter, Depends, status

from ..db import schemas
from ..dependencies.auth import CurrentUser, get_current_user
from ..dependencies.components import get_portfolio_service
from ..interfaces import IPortfolioService

router = APIRouter(
    prefix="/api/portfolios",
    tags=["portfolios"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=schemas.PortfolioOut, status_code=status.HTTP_201_CREATED)
def criar_carteira(
    portfolio_in: schemas.PortfolioCreate,
    current_user: CurrentUser,
    portfolios: IPortfolioService = Depends(get_portfolio_service),
):
    """UC02 - Cadastrar carteira do usuário autenticado."""
    return portfolios.create_portfolio(current_user.user_id, portfolio_in)


@router.get("", response_model=list[schemas.PortfolioOut])
def listar_carteiras(
    current_user: CurrentUser,
    portfolios: IPortfolioService = Depends(get_portfolio_service),
):
    """UC02 - Consultar as carteiras do usuário autenticado."""
    return portfolios.list_portfolios(current_user.user_id)


@router.get("/{portfolio_id}", response_model=schemas.PortfolioOut)
def consultar_carteira(
    portfolio_id: int,
    current_user: CurrentUser,
    portfolios: IPortfolioService = Depends(get_portfolio_service),
):
    """UC02 - Consultar uma carteira pelo identificador."""
    return portfolios.get_portfolio(current_user.user_id, portfolio_id)


@router.patch("/{portfolio_id}", response_model=schemas.PortfolioOut)
def editar_carteira(
    portfolio_id: int,
    portfolio_in: schemas.PortfolioUpdate,
    current_user: CurrentUser,
    portfolios: IPortfolioService = Depends(get_portfolio_service),
):
    """UC02 - Editar nome e/ou descrição da carteira."""
    return portfolios.update_portfolio(current_user.user_id, portfolio_id, portfolio_in)


@router.delete("/{portfolio_id}", response_model=schemas.MessageResponse)
def remover_carteira(
    portfolio_id: int,
    current_user: CurrentUser,
    portfolios: IPortfolioService = Depends(get_portfolio_service),
):
    """UC02 - Remover a carteira. As operações dos ativos continuam registradas."""
    portfolios.delete_portfolio(current_user.user_id, portfolio_id)
    return schemas.MessageResponse(message="Carteira removida.")
