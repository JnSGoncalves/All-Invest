from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import crud, schemas
from ..db.database import get_db
from ..dependencies.auth import CurrentUser
from ..services import ticker_services

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

# Catálogo provisório até existir o cadastro de corretoras. As operações, no
# entanto, são persistidas com a corretora correspondente no Supabase.
MOCK_BROKERS = {1: "XP Investimentos", 2: "Rico", 3: "Clear", 4: "NuInvest"}
BROKER_IDS_BY_NAME = {name: broker_id for broker_id, name in MOCK_BROKERS.items()}


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
    db: Session = Depends(get_db),
):
    """Registra uma compra ou venda do usuário identificado pelo Bearer JWT."""
    ticker_info = await ticker_services.validar_ticker(trade_in.stock_name)
    ticker = ticker_info["stock_name"]
    company_name = ticker_info["company_name"]
    stock_price = (
        await ticker_services.obter_cotacao(ticker)
        if trade_in.auto_cotacao
        else trade_in.stock_price
    )

    broker_name = MOCK_BROKERS.get(trade_in.broker_id)
    if broker_name is None:
        raise HTTPException(status_code=400, detail="Corretora não cadastrada.")

    try:
        # FOR UPDATE protege a checagem contra duas vendas simultâneas.
        if trade_in.trade_side == "SELL":
            balance = crud.get_user_stock_balance(
                db, user_id=current_user.user_id, stock_name=ticker, lock=True
            )
            if trade_in.stock_quantity > balance:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(f"Saldo insuficiente para venda. Posição atual de {ticker}: "
                            f"{balance} ação(ões)."),
                )

        stock = crud.get_or_create_stock(db, ticker, company_name)
        broker = crud.get_or_create_broker(db, broker_name)
        crud.ensure_user_broker(
            db, user_id=current_user.user_id, broker_id=broker.broker_id
        )
        trade = crud.create_user_stock(
            db,
            user_id=current_user.user_id,
            stock_id=stock.stock_id,
            broker_id=broker.broker_id,
            stock_quantity=trade_in.stock_quantity,
            stock_price=stock_price,
            trade_side=trade_in.trade_side,
            trade_date=trade_in.trade_date or datetime.now(timezone.utc),
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma operação com o mesmo ativo e horário.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível salvar a operação. Tente novamente.",
        ) from exc

    return _trade_out(trade)


@router.get("", response_model=list[schemas.StockTradeOut])
def listar_operacoes(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Lista as operações persistidas da carteira autenticada."""
    return [_trade_out(trade) for trade in crud.get_user_stock_trades(db, current_user.user_id)]


@router.get("/carteira", response_model=list[schemas.PositionOut])
def consultar_carteira(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Consolida quantidade e preço médio a partir das operações persistidas."""
    positions: dict[str, dict] = {}
    for trade in reversed(crud.get_user_stock_trades(db, current_user.user_id)):
        ticker = trade.stock.stock_name
        position = positions.setdefault(
            ticker,
            {"stock_name": ticker, "company_name": trade.stock.company_name,
             "stock_quantity": 0, "cost_basis": Decimal("0")},
        )
        if trade.trade_side == "BUY":
            position["stock_quantity"] += trade.stock_quantity
            position["cost_basis"] += trade.stock_price * trade.stock_quantity
        elif position["stock_quantity"]:
            average = position["cost_basis"] / position["stock_quantity"]
            position["stock_quantity"] -= trade.stock_quantity
            position["cost_basis"] -= average * trade.stock_quantity

    return [
        {
            "stock_name": position["stock_name"],
            "company_name": position["company_name"],
            "stock_quantity": position["stock_quantity"],
            "preco_medio": (position["cost_basis"] / position["stock_quantity"])
            .quantize(Decimal("0.0001")),
        }
        for position in positions.values()
        if position["stock_quantity"] > 0
    ]


@router.get("/validar/{stock_name}", response_model=schemas.StockValidationOut)
async def validar_ativo(stock_name: str):
    """Verifica se um ticker existe e está ativo na B3."""
    ticker_info = await ticker_services.validar_ticker(stock_name)
    return {**ticker_info, "valido": True}


@router.get("/buscar", response_model=schemas.TickerListOut)
async def buscar_tickers(search: str | None = None, tipo: str | None = None,
                         page: int = 1, limit: int = 20):
    return await ticker_services.listar_tickers(search=search, tipo=tipo, page=page, limit=limit)


@router.get("/autocomplete", response_model=list[schemas.TickerAutocompleteOut])
async def autocomplete_tickers(q: str, limit: int = 8):
    return await ticker_services.autocomplete_tickers(q, limit=limit)
