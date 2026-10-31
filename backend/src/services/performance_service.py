"""Valorização em reais, descontando aportes e incluindo proventos registrados."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas
from ..interfaces import IMarketDataService

MARKET_ZONE = ZoneInfo("America/Sao_Paulo")
ZERO = Decimal("0")
MONEY_FIELDS = ("opening_value", "closing_value", "purchases", "sales", "income", "gain")


def market_day(value: datetime) -> date:
    # SQLite omite o fuso; todas as gravações são normalizadas em UTC.
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(MARKET_ZONE).date()


def percentage(gain: Decimal, capital: Decimal) -> Decimal | None:
    return (gain / capital * 100).quantize(Decimal("0.0001")) if capital else None


class PerformanceService:
    def __init__(self, db: Session, market_data: IMarketDataService):
        self._db = db
        self._market_data = market_data

    async def get_performance(self, user_id: int, start: date, end: date) -> schemas.PerformanceOut:
        if start < date(1970, 1, 11) or start > end or end > datetime.now(MARKET_ZONE).date() or (end - start).days > 3660:
            raise HTTPException(422, "Informe um período de até 10 anos, com início anterior ou igual ao fim e sem datas futuras.")
        grouped = {}
        for trade in crud.get_user_stock_trades(self._db, user_id):
            if market_day(trade.trade_date) <= end:
                grouped.setdefault(trade.stock.stock_name, []).append(trade)
        incomes = self._db.query(models.Income).filter_by(user_id=user_id).all()
        for item in incomes:
            if start <= market_day(item.received_at) <= end:
                grouped.setdefault(item.stock_name, [])
        assets = []
        for ticker, trades in sorted(grouped.items()):
            opening_qty = closing_qty = 0
            purchases = sales = ZERO
            for trade in trades:
                day = market_day(trade.trade_date)
                signed_qty = trade.stock_quantity * (1 if trade.trade_side == "BUY" else -1)
                closing_qty += signed_qty
                if day < start:
                    opening_qty += signed_qty
                else:
                    amount = trade.stock_price * trade.stock_quantity
                    if trade.trade_side == "BUY":
                        purchases += amount
                    else:
                        sales += amount
            income = sum((item.amount for item in incomes if item.stock_name == ticker
                          and start <= market_day(item.received_at) <= end), ZERO)
            if not (opening_qty or closing_qty or purchases or sales or income):
                continue
            history = []
            if opening_qty or closing_qty:
                history = await self._market_data.get_history(ticker, start - timedelta(days=10), end)

            def value_at(day, quantity):
                if not quantity:
                    return ZERO
                points = [point for point in history if point.date <= day and (day - point.date).days <= 7]
                if not points:
                    raise HTTPException(502, f"Cotação histórica indisponível para {ticker} em {day}.")
                return max(points, key=lambda point: point.date).close * quantity

            opening = value_at(start - timedelta(days=1), opening_qty)
            closing = value_at(end, closing_qty)
            gain = closing - opening - purchases + sales + income
            assets.append(schemas.AssetPerformance(
                stock_name=ticker, opening_value=opening, closing_value=closing,
                purchases=purchases, sales=sales, income=income, gain=gain,
                return_percent=percentage(gain, opening + purchases),
            ))
        totals = {field: sum((getattr(asset, field) for asset in assets), ZERO) for field in MONEY_FIELDS}
        return schemas.PerformanceOut(
            start=start, end=end, has_assets=bool(assets), assets=assets, **totals,
            return_percent=percentage(totals["gain"], totals["opening_value"] + totals["purchases"]),
        )
