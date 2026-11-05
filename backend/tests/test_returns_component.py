"""
Testes do Returns Component (HU08) e da busca de histórico com cache.

O Returns Component usa os componentes reais de Investment e Portfolio sobre
SQLite; só o Market Data é o stub do conftest, com histórico configurado.
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from src.db.schemas import PortfolioCreate, StockTradeCreate
from src.services import market_data_service
from src.services.returns_service import ReturnsService

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 28)
BRT = timezone(timedelta(hours=-3))
D = Decimal

PETR4_HISTORY = [
    (date(2026, 7, 30), D("29.00")),
    (date(2026, 9, 25), D("31.00")),
    (date(2026, 9, 28), D("32.00")),  # início do período de 1 mês
    (date(2026, 10, 15), D("35.00")),
    (date(2026, 10, 21), D("34.00")),  # início do período de 1 semana
    (date(2026, 10, 28), D("36.00")),
]


@pytest.fixture
def returns_service(investment_service, portfolio_service, market_data):
    market_data.histories["PETR4"] = PETR4_HISTORY
    return ReturnsService(investment_service, portfolio_service, market_data, today=lambda: TODAY)


async def register(service, user, ticker, qty, price, day, side="BUY", portfolio_id=None):
    await service.create_trade(
        user.user_id,
        StockTradeCreate(
            stock_name=ticker,
            stock_quantity=qty,
            stock_price=D(price),
            broker_id=1,
            trade_side=side,
            trade_date=datetime.combine(day, time(14, 0), BRT),
            portfolio_id=portfolio_id,
        ),
    )


async def test_usuario_sem_ativos_recebe_rendimento_vazio(returns_service, user, market_data):
    result = await returns_service.get_returns(user.user_id, "1mo")

    assert result.has_assets is False
    assert result.assets == [] and result.series == []
    assert result.gain == D("0")
    assert not [call for call in market_data.calls if call[0] == "get_price_history"]


async def test_posicao_anterior_ao_periodo_rende_pela_variacao_do_fechamento(
    returns_service, investment_service, user
):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 9, 1))

    result = await returns_service.get_returns(user.user_id, "1mo")

    asset = result.assets[0]
    assert result.start_date == date(2026, 9, 28)
    assert result.end_date == TODAY
    assert asset.start_price == D("32.00") and asset.end_price == D("36.00")
    # Valoriza do fechamento inicial (32) até o atual (36), não do preço pago (30).
    assert result.start_value == D("320.00")
    assert result.end_value == D("360.00")
    assert result.gain == D("40.00")
    assert result.gain_rate == D("0.1250")


async def test_compra_no_periodo_e_aporte_e_nao_rendimento(returns_service, investment_service, user):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 9, 1))
    await register(investment_service, user, "PETR4", 5, "35", date(2026, 10, 15))

    result = await returns_service.get_returns(user.user_id, "1mo")

    assert result.bought == D("175.00")
    assert result.end_value == D("540.00")
    assert result.gain == D("45.00")  # 540 - 320 - 175
    assert result.gain_rate == D("0.0909")  # 45 / (320 + 175)
    assert result.assets[0].end_quantity == 15


async def test_venda_no_periodo_entra_como_ganho_realizado(returns_service, investment_service, user):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 9, 1))
    await register(investment_service, user, "PETR4", 4, "35", date(2026, 10, 15), side="SELL")

    result = await returns_service.get_returns(user.user_id, "1mo")

    assert result.sold == D("140.00")
    assert result.end_value == D("216.00")
    assert result.gain == D("36.00")  # 216 + 140 - 320


async def test_serie_diaria_comeca_em_zero_e_termina_no_total(returns_service, investment_service, user):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 9, 1))
    await register(investment_service, user, "PETR4", 5, "35", date(2026, 10, 15))

    result = await returns_service.get_returns(user.user_id, "1mo")

    assert [point.date for point in result.series] == [
        date(2026, 9, 28), date(2026, 10, 15), date(2026, 10, 21), date(2026, 10, 28),
    ]
    assert result.series[0].gain == D("0.00")
    assert result.series[1].invested == D("495.00")  # 320 + compra de 175
    assert result.series[1].value == D("525.00")  # 15 x 35
    assert result.series[-1].gain == result.gain
    assert result.series[-1].value == result.end_value


async def test_periodo_max_compara_com_o_custo_e_nao_tem_serie(
    returns_service, investment_service, user, market_data
):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 3, 2))

    result = await returns_service.get_returns(user.user_id, "max")

    assert result.start_date == date(2026, 3, 2)
    assert result.start_value == D("0.00")
    assert result.bought == D("300.00")
    assert result.gain == D("60.00")
    assert result.gain_rate == D("0.2000")
    assert result.series == []
    # Só a cotação recente é necessária: a janela cabe no plano gratuito da brapi.
    _, _, start, end = next(call for call in market_data.calls if call[0] == "get_price_history")
    assert (end - start).days <= 90


async def test_janela_de_historico_nunca_passa_de_90_dias(
    returns_service, investment_service, user, market_data
):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 7, 1))

    for period in ("1w", "1mo", "3mo"):
        market_data.calls.clear()
        await returns_service.get_returns(user.user_id, period)
        _, _, start, end = next(call for call in market_data.calls if call[0] == "get_price_history")
        assert end == TODAY
        assert (end - start).days <= 90


async def test_ativo_sem_cotacao_fica_fora_dos_totais(returns_service, investment_service, user):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 9, 1))
    await register(investment_service, user, "VALE3", 3, "60", date(2026, 9, 1))

    result = await returns_service.get_returns(user.user_id, "1mo")

    assert result.unavailable == ["VALE3"]
    assert [asset.stock_name for asset in result.assets] == ["PETR4"]
    assert result.gain == D("40.00")


async def test_ativo_zerado_antes_do_periodo_nao_aparece(returns_service, investment_service, user):
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 8, 1))
    await register(investment_service, user, "PETR4", 10, "31", date(2026, 8, 20), side="SELL")

    result = await returns_service.get_returns(user.user_id, "1w")

    assert result.has_assets is True
    assert result.assets == []


async def test_filtro_por_carteira(returns_service, investment_service, portfolio_service, user, other_user, market_data):
    market_data.histories["VALE3"] = [(date(2026, 9, 28), D("60")), (TODAY, D("66"))]
    carteira = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Dividendos"))
    await register(investment_service, user, "PETR4", 10, "30", date(2026, 9, 1))
    await register(investment_service, user, "VALE3", 2, "55", date(2026, 9, 1), portfolio_id=carteira.portfolio_id)

    result = await returns_service.get_returns(user.user_id, "1mo", carteira.portfolio_id)

    assert [asset.stock_name for asset in result.assets] == ["VALE3"]
    assert result.assets[0].portfolio_name == "Dividendos"
    assert result.gain == D("12.00")

    alheia = portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Outra"))
    with pytest.raises(HTTPException) as exc:
        await returns_service.get_returns(user.user_id, "1mo", alheia.portfolio_id)
    assert exc.value.status_code == 404


# --- Market Data: histórico da brapi com cache ------------------------------


@pytest.fixture
def brapi_calls(monkeypatch):
    calls = []

    async def fake_get(path, params):
        calls.append((path, params))
        return {
            "results": [{
                "symbol": params["symbols"],
                "data": {"historicalDataPrice": [
                    # A brapi devolve do mais recente para o mais antigo.
                    {"date": 1793156400, "close": 52.47},  # 2026-10-28 03:00 UTC
                    {"date": 1793070000, "close": 52.79},  # 2026-10-27
                    {"date": 1792983600, "close": None},
                ]},
            }],
        }

    market_data_service._HISTORY_CACHE.clear()
    monkeypatch.setattr(market_data_service, "_get", fake_get)
    yield calls
    market_data_service._HISTORY_CACHE.clear()


async def test_historico_vem_em_ordem_crescente_e_usa_cache(brapi_calls):
    inicio, fim = date(2026, 10, 20), date(2026, 10, 28)

    primeira = await market_data_service.obter_historico("petr4", inicio, fim)
    segunda = await market_data_service.obter_historico("PETR4", inicio, fim)

    assert primeira == [(date(2026, 10, 27), D("52.79")), (date(2026, 10, 28), D("52.47"))]
    assert segunda == primeira
    assert len(brapi_calls) == 1
    path, params = brapi_calls[0]
    assert path == "/stocks/historical"
    assert params == {"symbols": "PETR4", "startDate": "2026-10-20", "endDate": "2026-10-28", "interval": "1d"}


async def test_cache_separa_ativo_e_periodo(brapi_calls):
    await market_data_service.obter_historico("PETR4", date(2026, 10, 20), date(2026, 10, 28))
    await market_data_service.obter_historico("PETR4", date(2026, 9, 28), date(2026, 10, 28))
    await market_data_service.obter_historico("VALE3", date(2026, 10, 20), date(2026, 10, 28))

    assert len(brapi_calls) == 3


async def test_historico_vazio_retorna_404(monkeypatch):
    async def fake_get(path, params):
        return {"results": []}

    market_data_service._HISTORY_CACHE.clear()
    monkeypatch.setattr(market_data_service, "_get", fake_get)

    with pytest.raises(HTTPException) as exc:
        await market_data_service.obter_historico("XPTO3", date(2026, 10, 20), date(2026, 10, 28))
    assert exc.value.status_code == 404


@pytest.fixture
def brapi_transport(monkeypatch):
    """Substitui a rede do _get por respostas programadas (httpx.MockTransport)."""
    responses = []
    requests = []

    def handler(request):
        requests.append(request)
        return responses.pop(0)

    real_client = market_data_service.httpx.AsyncClient
    monkeypatch.setattr(
        market_data_service.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=market_data_service.httpx.MockTransport(handler), **kwargs),
    )
    monkeypatch.setattr(market_data_service.asyncio, "sleep", _no_sleep)
    return responses, requests


async def _no_sleep(_seconds):
    return None


async def test_429_curto_e_repetido_uma_vez(brapi_transport):
    responses, requests = brapi_transport
    responses += [
        market_data_service.httpx.Response(429, headers={"Retry-After": "1"}),
        market_data_service.httpx.Response(200, json={"results": []}),
    ]

    assert await market_data_service._get("/stocks/historical", {"symbols": "PETR4"}) == {"results": []}
    assert len(requests) == 2


async def test_429_persistente_vira_erro_429(brapi_transport):
    responses, requests = brapi_transport
    responses += [market_data_service.httpx.Response(429), market_data_service.httpx.Response(429)]

    with pytest.raises(HTTPException) as exc:
        await market_data_service._get("/stocks/historical", {"symbols": "PETR4"})
    assert exc.value.status_code == 429
    assert len(requests) == 2


async def test_limite_do_plano_repassa_mensagem_da_brapi(brapi_transport):
    responses, _ = brapi_transport
    responses.append(market_data_service.httpx.Response(
        400, json={"error": True, "message": "Seu plano permite no máximo 90 dias de dados históricos."}
    ))

    with pytest.raises(HTTPException) as exc:
        await market_data_service._get("/stocks/historical", {"symbols": "BBAS3"})
    assert exc.value.status_code == 502
    assert "90 dias" in exc.value.detail
