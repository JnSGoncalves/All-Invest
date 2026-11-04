"""
Returns Component (HU08): rendimento da carteira no período selecionado.

Cruza as operações registradas pelo usuário com os fechamentos históricos da
B3 e calcula, por ativo e no total:

    ganho = valor final + vendas no período - valor inicial - compras no período

O valor inicial é a posição no fim do dia de início valorizada pelo
fechamento daquele dia; o valor final usa o fechamento mais recente. Assim,
aportes e resgates não são confundidos com rendimento. A taxa divide o ganho
pelo capital do período (valor inicial + compras).

No período "max" (desde a primeira compra) o valor inicial é zero e basta a
cotação mais recente, então ele não esbarra no limite de 90 dias de histórico
do plano gratuito da brapi; por isso também não há série diária nesse período.
"""

from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from ..db import schemas
from ..interfaces import IInvestmentService, IMarketDataService, IPortfolioService

BRT = timezone(timedelta(hours=-3), "BRT")
PERIOD_DAYS: dict[str, int | None] = {"1w": 7, "1mo": 30, "3mo": 90, "max": None}
# Janela máxima de histórico aceita pela brapi no plano gratuito.
MAX_HISTORY_DAYS = 90
# Folga para achar o último pregão antes do início (fins de semana e feriados).
START_LOOKBACK_DAYS = 7

CENTS = Decimal("0.01")
RATE = Decimal("0.0001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS)


def _rate(gain: Decimal, base: Decimal) -> Decimal | None:
    return (gain / base).quantize(RATE) if base > 0 else None


def _local_date(moment: datetime) -> date:
    # SQLite devolve datetimes sem fuso; o banco grava em UTC.
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(BRT).date()


def _price_on(history: list[tuple[date, Decimal]], day: date) -> Decimal:
    """Último fechamento até `day`; antes do primeiro pregão usa o primeiro."""
    index = bisect_right(history, day, key=lambda point: point[0])
    return history[max(index - 1, 0)][1]


@dataclass
class _Flow:
    day: date
    quantity: int  # positivo na compra, negativo na venda
    amount: Decimal  # positivo na compra, negativo na venda


@dataclass
class _Asset:
    stock_id: int
    stock_name: str
    company_name: str
    start_quantity: int = 0
    flows: list[_Flow] = field(default_factory=list)


class ReturnsService:
    def __init__(
        self,
        investments: IInvestmentService,
        portfolios: IPortfolioService,
        market_data: IMarketDataService,
        today: Callable[[], date] | None = None,
    ) -> None:
        self._investments = investments
        self._portfolios = portfolios
        self._market_data = market_data
        self._today = today or (lambda: datetime.now(BRT).date())

    async def get_returns(
        self, user_id: int, period: schemas.ReturnPeriod, portfolio_id: int | None = None
    ) -> schemas.ReturnsOut:
        if portfolio_id is not None:
            self._portfolios.get_portfolio(user_id, portfolio_id)
        portfolios_by_stock = self._portfolios.get_investment_portfolios(user_id)

        trades = [
            trade
            for trade in self._investments.list_trades(user_id)
            if portfolio_id is None
            or getattr(portfolios_by_stock.get(trade.stock_id), "portfolio_id", None)
            == portfolio_id
        ]
        today = self._today()
        days = PERIOD_DAYS[period]

        if not trades:
            return self._empty(period, today, has_assets=False)

        trade_days = [_local_date(trade.trade_date) for trade in trades]
        if days is None:
            # Antes da primeira compra não havia posição: valor inicial zero.
            start = min(trade_days) - timedelta(days=1)
            fetch_start = today - timedelta(days=START_LOOKBACK_DAYS)
        else:
            start = today - timedelta(days=days)
            fetch_start = max(
                start - timedelta(days=START_LOOKBACK_DAYS),
                today - timedelta(days=MAX_HISTORY_DAYS),
            )

        assets: dict[str, _Asset] = {}
        for trade, day in sorted(zip(trades, trade_days), key=lambda item: item[0].trade_date):
            ticker = trade.stock.stock_name
            asset = assets.setdefault(
                ticker, _Asset(trade.stock_id, ticker, trade.stock.company_name)
            )
            sign = 1 if trade.trade_side == "BUY" else -1
            if day <= start:
                asset.start_quantity += sign * trade.stock_quantity
            else:
                asset.flows.append(
                    _Flow(day, sign * trade.stock_quantity, sign * trade.stock_price * trade.stock_quantity)
                )

        # Ativos zerados antes do início não fazem parte do período.
        active = [asset for asset in assets.values() if asset.start_quantity > 0 or asset.flows]
        if not active:
            return self._empty(period, today, has_assets=True, start=start)

        histories = await self._load_histories([asset.stock_name for asset in active], fetch_start, today)
        priced = [asset for asset in active if histories.get(asset.stock_name)]
        unavailable = sorted(asset.stock_name for asset in active if not histories.get(asset.stock_name))

        asset_rows = [
            self._asset_return(asset, histories[asset.stock_name], start, portfolios_by_stock)
            for asset in priced
        ]
        asset_rows.sort(key=lambda row: row.gain, reverse=True)

        start_value = sum((row.start_value for row in asset_rows), Decimal("0"))
        bought = sum((row.bought for row in asset_rows), Decimal("0"))
        sold = sum((row.sold for row in asset_rows), Decimal("0"))
        end_value = sum((row.end_value for row in asset_rows), Decimal("0"))
        gain = end_value + sold - start_value - bought
        end_date = max((histories[asset.stock_name][-1][0] for asset in priced), default=None)

        return schemas.ReturnsOut(
            period=period,
            start_date=start + timedelta(days=1) if days is None else start,
            end_date=end_date,
            has_assets=True,
            start_value=_money(start_value),
            bought=_money(bought),
            sold=_money(sold),
            end_value=_money(end_value),
            gain=_money(gain),
            gain_rate=_rate(gain, start_value + bought),
            assets=asset_rows,
            series=[] if days is None else self._series(priced, histories, start, end_date),
            unavailable=unavailable,
        )

    async def _load_histories(
        self, tickers: list[str], start: date, end: date
    ) -> dict[str, list[tuple[date, Decimal]]]:
        # Em sequência: o plano gratuito da brapi aceita um ativo por requisição
        # e uma requisição por vez. Com o cache, as repetições não saem da API.
        histories = {}
        for ticker in tickers:
            try:
                histories[ticker] = await self._market_data.get_price_history(ticker, start, end)
            except HTTPException:
                # Sem cotação para um ativo, os demais continuam no relatório.
                histories[ticker] = []
        return histories

    @staticmethod
    def _asset_return(
        asset: _Asset,
        history: list[tuple[date, Decimal]],
        start: date,
        portfolios_by_stock: dict,
    ) -> schemas.AssetReturnOut:
        start_price = _price_on(history, start) if asset.start_quantity > 0 else None
        end_price = history[-1][1]
        end_quantity = asset.start_quantity + sum(flow.quantity for flow in asset.flows)

        start_value = asset.start_quantity * start_price if start_price is not None else Decimal("0")
        bought = sum((flow.amount for flow in asset.flows if flow.amount > 0), Decimal("0"))
        sold = -sum((flow.amount for flow in asset.flows if flow.amount < 0), Decimal("0"))
        end_value = end_quantity * end_price
        gain = end_value + sold - start_value - bought
        portfolio = portfolios_by_stock.get(asset.stock_id)

        return schemas.AssetReturnOut(
            stock_name=asset.stock_name,
            company_name=asset.company_name,
            portfolio_name=portfolio.portfolio_name if portfolio else None,
            start_quantity=asset.start_quantity,
            end_quantity=end_quantity,
            start_price=_money(start_price) if start_price is not None else None,
            end_price=_money(end_price),
            start_value=_money(start_value),
            bought=_money(bought),
            sold=_money(sold),
            end_value=_money(end_value),
            gain=_money(gain),
            gain_rate=_rate(gain, start_value + bought),
        )

    @staticmethod
    def _series(
        assets: list[_Asset],
        histories: dict[str, list[tuple[date, Decimal]]],
        start: date,
        end_date: date | None,
    ) -> list[schemas.ReturnPointOut]:
        """Valor da carteira e ganho acumulado em cada pregão do período."""
        if end_date is None:
            return []
        days = sorted(
            {start}
            | {
                day
                for asset in assets
                for day, _ in histories[asset.stock_name]
                if start < day <= end_date
            }
        )

        points = []
        for day in days:
            invested = Decimal("0")
            value = Decimal("0")
            for asset in assets:
                history = histories[asset.stock_name]
                # Operações depois do último pregão entram no último ponto,
                # para a série terminar exatamente no total do período.
                applied = [flow for flow in asset.flows if flow.day <= day or day == end_date]
                quantity = asset.start_quantity + sum(flow.quantity for flow in applied)
                start_value = (
                    asset.start_quantity * _price_on(history, start)
                    if asset.start_quantity > 0
                    else Decimal("0")
                )
                invested += start_value + sum((flow.amount for flow in applied), Decimal("0"))
                value += quantity * _price_on(history, day)
            points.append(
                schemas.ReturnPointOut(
                    date=day,
                    invested=_money(invested),
                    value=_money(value),
                    gain=_money(value - invested),
                )
            )
        return points

    @staticmethod
    def _empty(
        period: schemas.ReturnPeriod,
        today: date,
        *,
        has_assets: bool,
        start: date | None = None,
    ) -> schemas.ReturnsOut:
        zero = Decimal("0.00")
        return schemas.ReturnsOut(
            period=period,
            start_date=start,
            end_date=today if has_assets else None,
            has_assets=has_assets,
            start_value=zero,
            bought=zero,
            sold=zero,
            end_value=zero,
            gain=zero,
            gain_rate=None,
            assets=[],
            series=[],
            unavailable=[],
        )
