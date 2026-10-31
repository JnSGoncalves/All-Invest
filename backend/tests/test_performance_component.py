from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from src import models
from src.db.schemas import HistoricalPrice, StockTradeCreate
from src.services.performance_service import PerformanceService


async def trade(service, user, day, quantity=10, price="20", side="BUY", ticker="PETR4"):
    return await service.create_trade(user.user_id, StockTradeCreate(
        stock_name=ticker, stock_quantity=quantity, stock_price=price,
        trade_side=side, broker_id=1, trade_date=datetime.fromisoformat(day),
    ))


@pytest.mark.anyio
async def test_periodo_cruza_compras_vendas_e_proventos(db, user, investment_service, market_data):
    await trade(investment_service, user, "2026-08-01T10:00:00+00:00")
    await trade(investment_service, user, "2026-09-03T10:00:00+00:00", quantity=5, price="25")
    await trade(investment_service, user, "2026-09-10T10:00:00+00:00", quantity=4, price="30", side="SELL")
    db.add(models.Income(user_id=user.user_id, stock_name="PETR4", amount=10,
                         received_at=datetime(2026, 9, 11, tzinfo=timezone.utc), kind="DIVIDEND"))
    db.commit()

    async def history(*args):
        return [HistoricalPrice(date=date(2026, 8, 31), close=22),
                HistoricalPrice(date=date(2026, 9, 30), close=28)]
    market_data.get_history = history
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    # 11*28 - 10*22 - 5*25 + 4*30 + 10 = 93; capital = 220 + 125.
    assert result.opening_value == 220
    assert result.closing_value == 308
    assert result.purchases == 125
    assert result.sales == 120
    assert result.income == 10
    assert result.gain == 93
    assert result.return_percent == Decimal("26.9565")


@pytest.mark.anyio
async def test_perda_e_soma_por_ativo(db, user, investment_service, market_data):
    for ticker in ("PETR4", "VALE3"):
        await trade(investment_service, user, "2026-09-01T10:00:00+00:00", ticker=ticker, price="40")
    market_data.quote = Decimal("30")
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    assert len(result.assets) == 2
    assert result.gain == -200
    assert result.return_percent == -25
    assert sum(asset.gain for asset in result.assets) == result.gain


@pytest.mark.anyio
async def test_posicao_encerrada_no_periodo_preserva_ganho(db, user, investment_service, market_data):
    await trade(investment_service, user, "2026-09-02T10:00:00+00:00")
    await trade(investment_service, user, "2026-09-03T10:00:00+00:00", price="25", side="SELL")
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    assert result.has_assets
    assert result.closing_value == 0
    assert result.gain == 50
    assert not any(call[0] == "get_history" for call in market_data.calls)


@pytest.mark.anyio
async def test_sem_ativos_e_isolamento_nao_consultam_fonte(db, user, other_user, investment_service, market_data):
    await trade(investment_service, other_user, "2026-09-01T10:00:00+00:00")
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    assert not result.has_assets
    assert result.gain == 0
    assert result.return_percent is None
    assert not any(call[0] == "get_history" for call in market_data.calls)


@pytest.mark.anyio
async def test_proventos_persistidos_sem_movimentacoes(db, user, market_data):
    db.add(models.Income(user_id=user.user_id, stock_name="PETR4", amount=10,
                         received_at=datetime(2026, 9, 1, tzinfo=timezone.utc), kind="DIVIDEND"))
    db.commit()
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 8, 31), date(2026, 9, 1))
    assert result.gain == 10
    assert result.return_percent is None


@pytest.mark.anyio
@pytest.mark.parametrize("start,end", [("2026-09-30", "2026-09-01"), ("2026-01-01", "2999-01-01"), ("2000-01-01", "2026-01-01"), ("0001-01-01", "0001-01-02")])
async def test_periodo_invalido(db, user, market_data, start, end):
    with pytest.raises(HTTPException) as error:
        await PerformanceService(db, market_data).get_performance(user.user_id, date.fromisoformat(start), date.fromisoformat(end))
    assert error.value.status_code == 422


@pytest.mark.anyio
async def test_fuso_brasileiro_e_operacoes_futuras(db, user, investment_service, market_data):
    # 01/09 01:00 UTC pertence ao dia 31/08 em São Paulo.
    await trade(investment_service, user, "2026-09-01T01:00:00+00:00")
    await trade(investment_service, user, "2026-10-01T10:00:00+00:00", quantity=999)
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    assert result.purchases == 0
    assert result.opening_value == result.closing_value == Decimal("385")


@pytest.mark.anyio
async def test_feriado_usa_fechamento_anterior_sem_olhar_futuro(db, user, investment_service, market_data):
    await trade(investment_service, user, "2026-08-01T10:00:00+00:00")
    async def history(*args):
        return [HistoricalPrice(date=date(2026, 9, 4), close=25),
                HistoricalPrice(date=date(2026, 9, 8), close=999)]
    market_data.get_history = history
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 5), date(2026, 9, 7))
    assert result.gain == 0
    assert result.closing_value == 250


@pytest.mark.anyio
async def test_falta_cotacao_nao_inventa_rendimento(db, user, investment_service, market_data):
    await trade(investment_service, user, "2026-08-01T10:00:00+00:00")
    async def empty(*args):
        return []
    market_data.get_history = empty
    with pytest.raises(HTTPException) as error:
        await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    assert error.value.status_code == 502


@pytest.mark.anyio
async def test_operacao_com_fuso_persiste_instante_utc(db, user, investment_service, market_data):
    await trade(investment_service, user, "2026-09-01T00:30:00+05:00")
    result = await PerformanceService(db, market_data).get_performance(user.user_id, date(2026, 9, 1), date(2026, 9, 30))
    assert result.purchases == 0
    assert result.opening_value == result.closing_value == 385
