"""Implementação das operações de investimento já expostas pela API."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas
from ..interfaces import IMarketDataService
from .investment_catalog import MOCK_BROKERS


class InvestmentService:
    def __init__(self, db: Session, market_data: IMarketDataService) -> None:
        self._db = db
        self._market_data = market_data

    async def create_trade(
        self, user_id: int, trade_in: schemas.StockTradeCreate
    ) -> models.UserStock:
        ticker_info = await self._market_data.validate_ticker(trade_in.stock_name)
        ticker = ticker_info["stock_name"]
        company_name = ticker_info["company_name"]
        stock_price = (
            await self._market_data.get_quote(ticker)
            if trade_in.auto_cotacao
            else trade_in.stock_price
        )

        broker_name = MOCK_BROKERS.get(trade_in.broker_id)
        if broker_name is None:
            raise HTTPException(status_code=400, detail="Corretora não cadastrada.")

        try:
            if trade_in.trade_side == "SELL":
                balance = crud.get_user_stock_balance(
                    self._db, user_id=user_id, stock_name=ticker, lock=True
                )
                if trade_in.stock_quantity > balance:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Saldo insuficiente para venda. Posição atual de {ticker}: "
                            f"{balance} ação(ões)."
                        ),
                    )

            stock = crud.get_or_create_stock(self._db, ticker, company_name)
            broker = crud.get_or_create_broker(self._db, broker_name)
            crud.ensure_user_broker(
                self._db, user_id=user_id, broker_id=broker.broker_id
            )
            return crud.create_user_stock(
                self._db,
                user_id=user_id,
                stock_id=stock.stock_id,
                broker_id=broker.broker_id,
                stock_quantity=trade_in.stock_quantity,
                stock_price=stock_price,
                trade_side=trade_in.trade_side,
                trade_date=trade_in.trade_date or datetime.now(timezone.utc),
            )
        except HTTPException:
            self._db.rollback()
            raise
        except IntegrityError as exc:
            self._db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma operação com o mesmo ativo e horário.",
            ) from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível salvar a operação. Tente novamente.",
            ) from exc

    def list_trades(self, user_id: int) -> list[models.UserStock]:
        return crud.get_user_stock_trades(self._db, user_id)

    def get_positions(self, user_id: int) -> list[schemas.PositionOut]:
        positions: dict[str, dict] = {}
        for trade in reversed(self.list_trades(user_id)):
            ticker = trade.stock.stock_name
            position = positions.setdefault(
                ticker,
                {
                    "stock_name": ticker,
                    "company_name": trade.stock.company_name,
                    "stock_quantity": 0,
                    "cost_basis": Decimal("0"),
                },
            )
            if trade.trade_side == "BUY":
                position["stock_quantity"] += trade.stock_quantity
                position["cost_basis"] += trade.stock_price * trade.stock_quantity
            elif position["stock_quantity"]:
                average = position["cost_basis"] / position["stock_quantity"]
                position["stock_quantity"] -= trade.stock_quantity
                position["cost_basis"] -= average * trade.stock_quantity

        return [
            schemas.PositionOut(
                stock_name=position["stock_name"],
                company_name=position["company_name"],
                stock_quantity=position["stock_quantity"],
                preco_medio=(
                    position["cost_basis"] / position["stock_quantity"]
                ).quantize(Decimal("0.0001")),
            )
            for position in positions.values()
            if position["stock_quantity"] > 0
        ]
