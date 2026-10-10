"""
Teste ponta a ponta pela API HTTP: rotas -> injeção de dependências ->
Investment Component -> IPortfolioService -> Portfolio Component -> banco.

Somente a autenticação (usuário fixo), a API key e o Market Data são
substituídos; a ligação entre os componentes é a mesma da produção
(dependencies/components.py).
"""

import pytest
from fastapi.testclient import TestClient

from src import main
from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.dependencies.components import get_market_data_service

API_KEY = "chave-de-teste"


@pytest.fixture
def client(monkeypatch, db, user, market_data):
    monkeypatch.setattr(main, "validate_api_key", lambda _db, key: key == API_KEY)
    monkeypatch.setattr(main, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)

    main.app.dependency_overrides[get_db] = lambda: db
    main.app.dependency_overrides[get_current_user] = lambda: user
    main.app.dependency_overrides[get_market_data_service] = lambda: market_data

    with TestClient(main.app, headers={"X-API-Key": API_KEY}) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def test_fluxo_completo_carteira_e_investimento(client):
    # Portfolio Component: criarCarteira
    response = client.post(
        "/api/portfolios",
        json={"portfolio_name": "Dividendos", "description": "Ações pagadoras"},
    )
    assert response.status_code == 201, response.text
    dividendos = response.json()

    response = client.post("/api/portfolios", json={"portfolio_name": "Trade"})
    trade_id = response.json()["portfolio_id"]

    # Investment Component: registrarMovimentacao já associando à carteira
    response = client.post(
        "/api/stocks",
        json={
            "stock_name": "petr4",
            "stock_quantity": 100,
            "stock_price": "37.25",
            "broker_id": 1,
            "trade_side": "BUY",
            "trade_date": "2026-09-01T10:00:00Z",
            "portfolio_id": dividendos["portfolio_id"],
        },
    )
    assert response.status_code == 201, response.text

    # consultarInvestimentos filtrado pela carteira
    response = client.get(
        "/api/stocks/carteira", params={"portfolio_id": dividendos["portfolio_id"]}
    )
    assert response.status_code == 200
    [position] = response.json()
    assert position["stock_name"] == "PETR4"
    assert position["portfolio_name"] == "Dividendos"

    # editarInvestimento: move o ativo para outra carteira
    response = client.put("/api/stocks/PETR4/portfolio", json={"portfolio_id": trade_id})
    assert response.status_code == 200
    assert response.json()["portfolio_name"] == "Trade"

    # editarCarteira
    response = client.patch(f"/api/portfolios/{trade_id}", json={"portfolio_name": "Swing Trade"})
    assert response.status_code == 200
    assert response.json()["portfolio_name"] == "Swing Trade"

    # removerCarteira: posição continua, sem carteira
    response = client.delete(f"/api/portfolios/{trade_id}")
    assert response.status_code == 200
    [position] = client.get("/api/stocks/carteira").json()
    assert position["stock_quantity"] == 100
    assert position["portfolio_id"] is None

    # consultarCarteira (lista)
    names = [p["portfolio_name"] for p in client.get("/api/portfolios").json()]
    assert names == ["Dividendos"]


def test_registrar_operacao_em_carteira_inexistente_retorna_404(client):
    response = client.post(
        "/api/stocks",
        json={
            "stock_name": "VALE3",
            "stock_quantity": 1,
            "stock_price": "60.00",
            "broker_id": 1,
            "trade_side": "BUY",
            "portfolio_id": 999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Carteira não encontrada."
    assert client.get("/api/stocks").json() == []


def test_criar_carteira_com_nome_repetido_retorna_409(client):
    client.post("/api/portfolios", json={"portfolio_name": "Longo Prazo"})

    response = client.post("/api/portfolios", json={"portfolio_name": "longo prazo"})

    assert response.status_code == 409


def test_editar_carteira_sem_campos_retorna_422(client):
    portfolio_id = client.post("/api/portfolios", json={"portfolio_name": "Trade"}).json()["portfolio_id"]

    response = client.patch(f"/api/portfolios/{portfolio_id}", json={})

    assert response.status_code == 422


def test_rotas_de_carteira_exigem_api_key(client):
    response = client.get("/api/portfolios", headers={"X-API-Key": "chave-errada"})

    assert response.status_code == 401
