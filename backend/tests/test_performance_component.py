"""
Testes do Serviço de Desempenho da Carteira (Performance Component, Lab 7).

Cobrem o contrato pela API REST: rotas -> injeção de dependências ->
PerformanceService -> Investment/Portfolio reais -> banco. Somente a autenticação
e o Market Data são simulados.
"""

import asyncio
from decimal import Decimal

import pytest
from fastapi import HTTPException, status

from src import main
from src.dependencies.auth import get_current_user
from src.services import performance_service

POSITIONS_URL = "/api/performance/portfolios/{}/positions"
PORTFOLIO_URL = "/api/performance/portfolios/{}"


def _portfolio(client, name="Dividendos") -> int:
    response = client.post("/api/portfolios", json={"portfolio_name": name})
    assert response.status_code == 201, response.text
    return response.json()["portfolio_id"]


def _buy(client, portfolio_id, ticker="PETR4", quantity=10, price="30.00", side="BUY"):
    response = client.post(
        "/api/stocks",
        json={
            "stock_name": ticker,
            "stock_quantity": quantity,
            "stock_price": price,
            "broker_id": 1,
            "trade_side": side,
            "portfolio_id": portfolio_id,
        },
    )
    assert response.status_code == 201, response.text


# --- avaliarPosicoes ---------------------------------------------------------

def test_avaliar_posicoes_devolve_os_campos_do_contrato(client, market_data):
    market_data.quotes["PETR4"] = Decimal("33.50")
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)

    response = client.get(POSITIONS_URL.format(portfolio_id))

    assert response.status_code == 200
    position = response.json()[0]
    assert set(position) == {
        "stock_name",
        "company_name",
        "stock_quantity",
        "preco_medio",
        "portfolio_id",
        "portfolio_name",
        "current_price",
        "invested_value",
        "market_value",
    }
    assert position["stock_name"] == "PETR4"
    assert position["stock_quantity"] == 10
    assert position["portfolio_id"] == portfolio_id
    assert position["portfolio_name"] == "Dividendos"
    assert Decimal(position["preco_medio"]) == Decimal("30")
    assert Decimal(position["current_price"]) == Decimal("33.50")
    assert Decimal(position["invested_value"]) == Decimal("300")
    assert Decimal(position["market_value"]) == Decimal("335")


def test_avaliar_posicoes_considera_somente_a_carteira_informada(client):
    primeira = _portfolio(client, "Primeira")
    segunda = _portfolio(client, "Segunda")
    _buy(client, primeira, "PETR4")
    _buy(client, segunda, "VALE3")

    tickers = [item["stock_name"] for item in client.get(POSITIONS_URL.format(primeira)).json()]

    assert tickers == ["PETR4"]


def test_avaliar_posicoes_de_carteira_vazia_retorna_lista_vazia(client):
    response = client.get(POSITIONS_URL.format(_portfolio(client)))

    assert response.status_code == 200
    assert response.json() == []


def test_avaliar_posicoes_ignora_ativo_zerado(client):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)
    _buy(client, portfolio_id, side="SELL")

    assert client.get(POSITIONS_URL.format(portfolio_id)).json() == []


# --- Erros previstos no contrato --------------------------------------------

def test_carteira_inexistente_retorna_404(client):
    response = client.get(POSITIONS_URL.format(999))

    assert response.status_code == 404
    assert response.json()["detail"] == "Carteira não encontrada."


def test_carteira_de_outro_usuario_retorna_404(client, other_user):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)

    main.app.dependency_overrides[get_current_user] = lambda: other_user

    assert client.get(POSITIONS_URL.format(portfolio_id)).status_code == 404
    assert client.get(PORTFOLIO_URL.format(portfolio_id)).status_code == 404


def test_cotacao_nao_encontrada_retorna_404(client, market_data):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)
    market_data.quotes["PETR4"] = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada para 'PETR4'."
    )
    performance_service._QUOTE_CACHE.clear()

    response = client.get(POSITIONS_URL.format(portfolio_id))

    assert response.status_code == 404
    assert response.json()["detail"] == "Cotação não encontrada para 'PETR4'."


@pytest.mark.parametrize("portfolio_id", ["0", "-1", "abc"])
def test_portfolio_id_invalido_retorna_422(client, portfolio_id):
    assert client.get(POSITIONS_URL.format(portfolio_id)).status_code == 422


def test_sem_autenticacao_retorna_401(client):
    del main.app.dependency_overrides[get_current_user]

    response = client.get(POSITIONS_URL.format(1))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("api_key", [None, "chave-errada"])
def test_chave_de_api_invalida_retorna_401(client, api_key):
    client.headers.pop("X-API-Key", None)
    headers = {} if api_key is None else {"X-API-Key": api_key}

    assert client.get(POSITIONS_URL.format(1), headers=headers).status_code == 401


def test_timeout_do_market_data_retorna_504(client, market_data):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)
    market_data.quotes["PETR4"] = HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        detail="Tempo de resposta da brapi.dev excedido. Tente novamente.",
    )
    performance_service._QUOTE_CACHE.clear()

    assert client.get(POSITIONS_URL.format(portfolio_id)).status_code == 504


def test_consulta_que_excede_o_limite_total_retorna_504(client, market_data, monkeypatch):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)
    performance_service._QUOTE_CACHE.clear()

    async def slow_quote(_ticker):
        await asyncio.sleep(1)

    monkeypatch.setattr(performance_service, "QUOTES_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(market_data, "get_quote", slow_quote)

    response = client.get(POSITIONS_URL.format(portfolio_id))

    assert response.status_code == 504
    assert response.json()["detail"].startswith("Tempo de consulta")


# --- consultarDesempenhoAcao -------------------------------------------------

def test_desempenho_da_acao_com_ganho(client, market_data):
    market_data.quotes["PETR4"] = Decimal("33")
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)

    response = client.get(f"{POSITIONS_URL.format(portfolio_id)}/petr4")

    assert response.status_code == 200
    body = response.json()
    assert body["stock_name"] == "PETR4"
    assert Decimal(body["invested_value"]) == Decimal("300")
    assert Decimal(body["market_value"]) == Decimal("330")
    assert Decimal(body["gain"]) == Decimal("30")
    assert Decimal(body["profitability_pct"]) == Decimal("10")


def test_desempenho_da_acao_com_perda(client, market_data):
    market_data.quotes["VALE3"] = Decimal("45")
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id, "VALE3", 4, "60")

    body = client.get(f"{POSITIONS_URL.format(portfolio_id)}/VALE3").json()

    assert Decimal(body["gain"]) == Decimal("-60")
    assert Decimal(body["profitability_pct"]) == Decimal("-25")


def test_acao_fora_da_carteira_retorna_404(client):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)

    response = client.get(f"{POSITIONS_URL.format(portfolio_id)}/VALE3")

    assert response.status_code == 404
    assert "VALE3" in response.json()["detail"]


# --- obterDesempenhoCarteira -------------------------------------------------

def test_rentabilidade_da_carteira_usa_os_totais_e_nao_a_media(client, market_data):
    market_data.quotes.update({"PETR4": Decimal("33"), "VALE3": Decimal("30")})
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id, "PETR4", 100, "30")  # investe 3000 e ganha 10%
    _buy(client, portfolio_id, "VALE3", 1, "60")  # investe 60 e perde 50%

    response = client.get(PORTFOLIO_URL.format(portfolio_id))

    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_id"] == portfolio_id
    assert body["portfolio_name"] == "Dividendos"
    assert Decimal(body["total_invested"]) == Decimal("3060")
    assert Decimal(body["total_market_value"]) == Decimal("3330")
    assert Decimal(body["total_gain"]) == Decimal("270")
    # A média simples das ações daria -20%; pelos totais são 270 / 3060.
    assert Decimal(body["profitability_pct"]) == Decimal("8.82")
    assert {item["stock_name"]: Decimal(item["profitability_pct"]) for item in body["positions"]} == {
        "PETR4": Decimal("10"),
        "VALE3": Decimal("-50"),
    }


def test_preco_medio_apos_compras_e_venda_entra_no_calculo(client, market_data):
    market_data.quotes["PETR4"] = Decimal("40")
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id, quantity=10, price="30")
    _buy(client, portfolio_id, quantity=10, price="20")
    _buy(client, portfolio_id, quantity=5, price="50", side="SELL")

    body = client.get(PORTFOLIO_URL.format(portfolio_id)).json()

    assert Decimal(body["total_invested"]) == Decimal("375")  # 15 x preço médio de 25
    assert Decimal(body["total_market_value"]) == Decimal("600")
    assert Decimal(body["total_gain"]) == Decimal("225")


def test_carteira_vazia_tem_totais_zerados_sem_rentabilidade(client):
    body = client.get(PORTFOLIO_URL.format(_portfolio(client))).json()

    assert Decimal(body["total_invested"]) == 0
    assert Decimal(body["total_gain"]) == 0
    assert body["profitability_pct"] is None
    assert body["positions"] == []


# --- Cache de cotações e recálculo assíncrono --------------------------------

def _quote_calls(market_data) -> int:
    return sum(1 for call in market_data.calls if call[0] == "get_quote")


def test_consultas_em_sequencia_reaproveitam_a_cotacao(client, market_data):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)
    before = _quote_calls(market_data)

    client.get(POSITIONS_URL.format(portfolio_id))
    client.get(PORTFOLIO_URL.format(portfolio_id))

    assert _quote_calls(market_data) == before


def test_cotacao_expirada_e_consultada_de_novo(client, market_data, monkeypatch):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id)
    before = _quote_calls(market_data)
    monkeypatch.setattr(performance_service, "QUOTE_TTL_SECONDS", -1)
    performance_service._QUOTE_CACHE.clear()

    client.get(POSITIONS_URL.format(portfolio_id))
    client.get(POSITIONS_URL.format(portfolio_id))

    assert _quote_calls(market_data) == before + 2


def test_compra_e_venda_acionam_o_recalculo_em_segundo_plano(client, market_data):
    portfolio_id = _portfolio(client)
    _buy(client, portfolio_id, price="30")
    market_data.quotes["PETR4"] = Decimal("35")

    # A cotação nova só entra depois de outra operação, sem esperar o cache expirar.
    assert Decimal(client.get(POSITIONS_URL.format(portfolio_id)).json()[0]["market_value"]) == Decimal("385")

    _buy(client, portfolio_id, quantity=1, side="SELL")

    position = client.get(POSITIONS_URL.format(portfolio_id)).json()[0]
    assert position["stock_quantity"] == 9
    assert Decimal(position["current_price"]) == Decimal("35")
    assert Decimal(position["market_value"]) == Decimal("315")


def test_falha_no_recalculo_nao_afeta_a_operacao(client, market_data):
    portfolio_id = _portfolio(client)
    market_data.quotes["PETR4"] = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada."
    )

    _buy(client, portfolio_id)

    assert len(client.get("/api/stocks").json()) == 1


@pytest.mark.anyio
async def test_recalculo_de_usuario_sem_posicoes_nao_consulta_cotacoes(
    performance_service_real, market_data, user
):
    await performance_service_real.recalculate(user.user_id)

    assert market_data.calls == []
