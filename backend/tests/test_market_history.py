from datetime import date, datetime, timezone

import httpx
import pytest
from fastapi import HTTPException

from src.services import market_data_service as market

START, END = date(2026, 9, 1), date(2026, 9, 30)


@pytest.fixture(autouse=True)
def clear_history_cache():
    market._HISTORY_CACHE.clear()
    yield
    market._HISTORY_CACHE.clear()


def payload(raw=25):
    return {"results": [{"symbol": "PETR4", "data": {"historicalDataPrice": [{
        "date": datetime(2026, 9, 1, 12, tzinfo=timezone.utc).timestamp(),
        "rawClose": raw, "close": 999, "adjustedClose": 999,
    }]}}]}


def mock_http(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(market.httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


@pytest.mark.anyio
async def test_contrato_real_http_e_cache_por_ativo_e_periodo(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.path == "/api/v2/stocks/historical"
        assert request.url.params["startDate"] == START.isoformat()
        assert request.url.params["interval"] == "1d"
        assert request.url.params["includeRaw"] == "true"
        assert request.headers["Authorization"] == "Bearer token-de-teste"
        return httpx.Response(200, json=payload())
    mock_http(monkeypatch, handler)
    service = market.BrapiMarketDataService()
    first = await service.get_history("petr4", START, END)
    first[0].close = 1  # Respostas não alteram o cache compartilhado.
    assert (await service.get_history("PETR4", START, END))[0].close == 25
    assert len(calls) == 1
    await service.get_history("PETR4", START, date(2026, 9, 29))
    assert len(calls) == 2


@pytest.mark.anyio
async def test_cache_expira_e_tem_limite(monkeypatch):
    calls = []
    clock = [10]
    monkeypatch.setattr(market, "monotonic", lambda: clock[0])
    monkeypatch.setattr(market, "_HISTORY_CACHE_SIZE", 1)
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=payload())
    mock_http(monkeypatch, handler)
    service = market.BrapiMarketDataService()
    await service.get_history("PETR4", START, END)
    clock[0] += market._HISTORY_TTL + 1
    await service.get_history("PETR4", START, END)
    assert len(calls) == 2
    await service.get_history("PETR4", START, date(2026, 9, 29))
    assert len(market._HISTORY_CACHE) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("code,expected", [(400, 502), (401, 502), (403, 502), (404, 502), (429, 429), (500, 502)])
async def test_erros_http_preservam_estado_sem_cache(monkeypatch, code, expected):
    mock_http(monkeypatch, lambda request: httpx.Response(code, json={"error": "provider"}))
    with pytest.raises(HTTPException) as error:
        await market.BrapiMarketDataService().get_history("PETR4", START, END)
    assert error.value.status_code == expected
    assert not market._HISTORY_CACHE


@pytest.mark.anyio
@pytest.mark.parametrize("data", [payload(None), payload(-1), payload("NaN"), {}, {"results": []}, payload("Infinity")])
async def test_dados_invalidos_nao_geram_precos_ficticios(monkeypatch, data):
    mock_http(monkeypatch, lambda request: httpx.Response(200, json=data))
    with pytest.raises(HTTPException) as error:
        await market.BrapiMarketDataService().get_history("PETR4", START, END)
    assert error.value.status_code == 502
    assert not market._HISTORY_CACHE


@pytest.mark.anyio
@pytest.mark.parametrize("exception,code", [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)])
async def test_erro_rede(monkeypatch, exception, code):
    def handler(request):
        raise exception("falha simulada", request=request)
    mock_http(monkeypatch, handler)
    with pytest.raises(HTTPException) as error:
        await market.BrapiMarketDataService().get_history("PETR4", START, END)
    assert error.value.status_code == code


@pytest.mark.anyio
async def test_json_invalido(monkeypatch):
    mock_http(monkeypatch, lambda request: httpx.Response(200, text="indisponível"))
    with pytest.raises(HTTPException) as error:
        await market.BrapiMarketDataService().get_history("PETR4", START, END)
    assert error.value.status_code == 502
