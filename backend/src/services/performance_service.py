"""
Performance Component (Lab 7): Serviço de Desempenho da Carteira.

Apura o resultado dos investimentos a preço de mercado, combinando as posições
do Investment Component com as cotações do Market Data:

    valor investido  = quantidade x preço médio
    valor de mercado = quantidade x cotação atual
    ganho ou perda   = valor de mercado - valor investido
    rentabilidade    = ganho ou perda / valor investido

A rentabilidade da carteira é calculada sobre os totais, não pela média das
ações, para que cada posição pese conforme o valor investido.

As posições são lidas a cada consulta; as cotações ficam em um cache curto,
para que consultas em sequência usem o mesmo preço e não gastem o limite da
brapi. Depois de uma compra ou venda, `recalculate` renova essas cotações em
segundo plano, sem atrasar a resposta da operação.
"""

import asyncio
import logging
import time
from decimal import Decimal

from fastapi import HTTPException, status

from ..db import schemas
from ..interfaces import IInvestmentService, IMarketDataService, IPortfolioService

# Sem configuração própria de logging, o uvicorn só exibe os próprios loggers.
logger = logging.getLogger("uvicorn.error")

# Cache em memória: ticker -> (expira_em, cotação).
_QUOTE_CACHE: dict[str, tuple[float, Decimal]] = {}
QUOTE_TTL_SECONDS = 60
# Limite para o conjunto de cotações de uma consulta; cada ativo já tem o timeout da brapi.
QUOTES_TIMEOUT_SECONDS = 20

CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS)


def _percentage(gain: Decimal, base: Decimal) -> Decimal | None:
    return _money(gain / base * 100) if base > 0 else None


class PerformanceService:
    def __init__(
        self,
        investments: IInvestmentService,
        portfolios: IPortfolioService,
        market_data: IMarketDataService,
    ) -> None:
        self._investments = investments
        self._portfolios = portfolios
        self._market_data = market_data

    async def evaluate_positions(
        self, user_id: int, portfolio_id: int
    ) -> list[schemas.PositionValuationOut]:
        return await self._valuate(self._investments.get_positions(user_id, portfolio_id))

    async def get_stock_performance(
        self, user_id: int, portfolio_id: int, stock_name: str
    ) -> schemas.StockPerformanceOut:
        ticker = stock_name.strip().upper()
        positions = self._investments.get_positions(user_id, portfolio_id)
        position = next((item for item in positions if item.stock_name == ticker), None)
        if position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A ação {ticker} não está nesta carteira.",
            )
        valuation = (await self._valuate([position]))[0]
        return self._performance(valuation)

    async def get_portfolio_performance(
        self, user_id: int, portfolio_id: int
    ) -> schemas.PortfolioPerformanceOut:
        portfolio = self._portfolios.get_portfolio(user_id, portfolio_id)
        positions = [
            self._performance(valuation)
            for valuation in await self.evaluate_positions(user_id, portfolio_id)
        ]

        total_invested = sum((item.invested_value for item in positions), Decimal("0.00"))
        total_market_value = sum((item.market_value for item in positions), Decimal("0.00"))
        total_gain = total_market_value - total_invested

        return schemas.PortfolioPerformanceOut(
            portfolio_id=portfolio.portfolio_id,
            portfolio_name=portfolio.portfolio_name,
            total_invested=total_invested,
            total_market_value=total_market_value,
            total_gain=total_gain,
            profitability_pct=_percentage(total_gain, total_invested),
            positions=positions,
        )

    async def evaluate_available(
        self, user_id: int, portfolio_id: int | None = None
    ) -> tuple[list[schemas.StockPerformanceOut], list[schemas.PositionOut]]:
        positions = self._investments.get_positions(user_id, portfolio_id)
        priced = []
        unavailable = list(positions)
        try:
            async with asyncio.timeout(QUOTES_TIMEOUT_SECONDS):
                for position in positions:
                    try:
                        current_price = await self._quote(position.stock_name, refresh=False)
                    except HTTPException:
                        continue
                    priced.append(self._performance(self._valuation(position, current_price)))
                    unavailable.remove(position)
        except TimeoutError:
            # As posições ainda não avaliadas seguem em `unavailable`.
            pass
        return priced, unavailable

    async def recalculate(self, user_id: int) -> None:
        try:
            positions = self._investments.get_positions(user_id)
            valuations = await self._valuate(positions, refresh=True)
        except HTTPException as exc:
            # A operação já foi gravada: a próxima consulta busca a cotação de novo.
            logger.warning(
                "Recálculo do desempenho falhou para o usuário %s: %s", user_id, exc.detail
            )
            return
        market_value = sum((item.market_value for item in valuations), Decimal("0.00"))
        logger.info(
            "Desempenho recalculado em segundo plano: usuário %s, %s posição(ões), "
            "valor de mercado R$ %s",
            user_id,
            len(valuations),
            market_value,
        )

    async def _valuate(
        self, positions: list[schemas.PositionOut], *, refresh: bool = False
    ) -> list[schemas.PositionValuationOut]:
        valuations = []
        try:
            async with asyncio.timeout(QUOTES_TIMEOUT_SECONDS):
                # Em sequência: o plano gratuito da brapi aceita uma requisição por vez.
                for position in positions:
                    current_price = await self._quote(position.stock_name, refresh)
                    valuations.append(self._valuation(position, current_price))
        except TimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Tempo de consulta das cotações excedido. Tente novamente.",
            ) from exc
        return valuations

    async def _quote(self, ticker: str, refresh: bool) -> Decimal:
        cached = _QUOTE_CACHE.get(ticker)
        if cached and not refresh and cached[0] > time.monotonic():
            return cached[1]
        quote = await self._market_data.get_quote(ticker)
        _QUOTE_CACHE[ticker] = (time.monotonic() + QUOTE_TTL_SECONDS, quote)
        return quote

    @staticmethod
    def _valuation(
        position: schemas.PositionOut, current_price: Decimal
    ) -> schemas.PositionValuationOut:
        return schemas.PositionValuationOut(
            **position.model_dump(),
            current_price=current_price,
            invested_value=_money(position.stock_quantity * position.preco_medio),
            market_value=_money(position.stock_quantity * current_price),
        )

    @staticmethod
    def _performance(valuation: schemas.PositionValuationOut) -> schemas.StockPerformanceOut:
        gain = valuation.market_value - valuation.invested_value
        return schemas.StockPerformanceOut(
            **valuation.model_dump(),
            gain=gain,
            profitability_pct=_percentage(gain, valuation.invested_value),
        )
