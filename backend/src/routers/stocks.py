from fastapi import APIRouter, Depends, status

from ..db import schemas
from ..dependencies.components import (
    get_investment_service,
    get_market_data_service,
)
from ..dependencies.auth import CurrentUser
from ..interfaces import IInvestmentService, IMarketDataService
from ..services.investment_catalog import BROKER_IDS_BY_NAME

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def _trade_out(trade) -> dict:
    return {
        "stock_name": trade.stock.stock_name,
        "company_name": trade.stock.company_name,
        "stock_quantity": trade.stock_quantity,
        "stock_price": trade.stock_price,
        # O contrato público usa o ID provisório do catálogo mockado, e não
        # a chave interna que o Supabase atribuiu à corretora.
        "broker_id": BROKER_IDS_BY_NAME.get(
            trade.broker.broker_name, trade.broker_id
        ),
        "broker_name": trade.broker.broker_name,
        "trade_side": trade.trade_side,
        "trade_date": trade.trade_date,
    }


@router.post("", response_model=schemas.StockTradeOut, status_code=status.HTTP_201_CREATED)
async def cadastrar_operacao(
    trade_in: schemas.StockTradeCreate,
    current_user: CurrentUser,
    investment_service: IInvestmentService = Depends(get_investment_service),
):
    """Registra uma compra ou venda do usuário identificado pelo Bearer JWT."""
    trade = await investment_service.create_trade(current_user.user_id, trade_in)
    return _trade_out(trade)


@router.get("", response_model=list[schemas.StockTradeOut])
def listar_operacoes(
    current_user: CurrentUser,
    investment_service: IInvestmentService = Depends(get_investment_service),
):
    """Lista as operações persistidas da carteira autenticada."""
    return [
        _trade_out(trade)
        for trade in investment_service.list_trades(current_user.user_id)
    ]


@router.get("/carteira", response_model=list[schemas.PositionOut])
def consultar_carteira(
    current_user: CurrentUser,
    investment_service: IInvestmentService = Depends(get_investment_service),
):
    """Consolida quantidade e preço médio a partir das operações persistidas."""
    return investment_service.get_positions(current_user.user_id)


@router.get("/validar/{stock_name}", response_model=schemas.StockValidationOut)
async def validar_ativo(
    stock_name: str,
    market_data: IMarketDataService = Depends(get_market_data_service),
):
    """Verifica se um ticker existe e está ativo na B3."""
    ticker_info = await market_data.validate_ticker(stock_name)
    return {**ticker_info, "valido": True}


@router.get("/buscar", response_model=schemas.TickerListOut)
async def buscar_tickers(
    search: str | None = None,
    tipo: str | None = None,
    page: int = 1,
    limit: int = 20,
    market_data: IMarketDataService = Depends(get_market_data_service),
):
    return await market_data.list_tickers(
        search=search, tipo=tipo, page=page, limit=limit
    )


@router.get("/autocomplete", response_model=list[schemas.TickerAutocompleteOut])
async def autocomplete_tickers(
    q: str,
    limit: int = 8,
    market_data: IMarketDataService = Depends(get_market_data_service),
):
    return await market_data.autocomplete_tickers(q, limit=limit)
