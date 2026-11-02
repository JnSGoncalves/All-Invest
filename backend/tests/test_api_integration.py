"""
Teste ponta a ponta pela API HTTP: rotas -> injeção de dependências ->
Investment Component -> IPortfolioService -> Portfolio Component -> banco.

Somente a autenticação (usuário fixo), a API key e o Market Data são
substituídos; a ligação entre os componentes é a mesma da produção
(dependencies/components.py).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src import main, models
from src.dependencies.auth import get_current_user
from src.dependencies.components import get_market_data_service


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


def test_rendimento_sem_ativos_informa_carteira_vazia(client):
    response = client.get("/api/rendimentos", params={"periodo": "1mo"})

    assert response.status_code == 200
    body = response.json()
    assert body["has_assets"] is False
    assert body["assets"] == [] and body["series"] == []


def test_rendimento_cruza_operacoes_com_historico(client, market_data):
    today = datetime.now(timezone(timedelta(hours=-3))).date()
    market_data.histories["PETR4"] = [
        (today - timedelta(days=40), Decimal("29")),
        (today, Decimal("33")),
    ]
    client.post(
        "/api/stocks",
        json={"stock_name": "PETR4", "stock_quantity": 10, "stock_price": "30", "broker_id": 1, "trade_side": "BUY"},
    )

    response = client.get("/api/rendimentos", params={"periodo": "1mo"})

    assert response.status_code == 200
    body = response.json()
    assert body["has_assets"] is True
    assert Decimal(body["bought"]) == Decimal("300")
    assert Decimal(body["end_value"]) == Decimal("330")
    assert Decimal(body["gain"]) == Decimal("30")
    assert body["assets"][0]["stock_name"] == "PETR4"
    assert Decimal(body["series"][-1]["gain"]) == Decimal("30")


def test_rendimento_rejeita_periodo_invalido(client):
    assert client.get("/api/rendimentos", params={"periodo": "10y"}).status_code == 422


def test_rendimento_exige_usuario_autenticado(client):
    del main.app.dependency_overrides[get_current_user]

    response = client.get("/api/rendimentos")

    assert response.status_code == 401


def test_listar_corretoras_somente_do_usuario(client, db, user, other_user):
    db.add_all([
        models.Broker(broker_id=103, broker_name="Outra corretora"),
        models.Broker(broker_id=104, broker_name="Sem vínculo"),
    ])
    db.flush()
    db.add_all([
        models.UserBroker(user_id=user.user_id, broker_id=1),
        models.UserBroker(user_id=user.user_id, broker_id=3),
        models.UserBroker(user_id=other_user.user_id, broker_id=3),
        models.UserBroker(user_id=other_user.user_id, broker_id=103),
    ])
    db.commit()

    response = client.get("/api/brokers", params={"user_id": other_user.user_id})

    assert response.status_code == 200
    assert response.json() == [
        {"broker_id": 3, "broker_name": "Clear"},
        {"broker_id": 1, "broker_name": "XP Investimentos"},
    ]


def test_listar_corretoras_sem_vinculos_retorna_lista_vazia(client, db, other_user):
    db.add(models.UserBroker(user_id=other_user.user_id, broker_id=1))
    db.commit()

    response = client.get("/api/brokers")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("authorization", [None, "Bearer token-invalido"])
def test_listar_corretoras_exige_autenticacao(client, authorization):
    main.app.dependency_overrides.pop(get_current_user)
    headers = {} if authorization is None else {"Authorization": authorization}

    response = client.get("/api/brokers", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("api_key", [None, "chave-errada"])
def test_listar_corretoras_exige_api_key(client, api_key):
    client.headers.pop("X-API-Key", None)
    headers = {} if api_key is None else {"X-API-Key": api_key}

    response = client.get("/api/brokers", headers=headers)

    assert response.status_code == 401


def test_cadastrar_corretora_e_registrar_operacao_por_ela(client):
    response = client.post("/api/brokers", json={"broker_name": "BTG Pactual"})
    assert response.status_code == 201, response.text
    broker = response.json()

    assert broker["broker_name"] in [item["broker_name"] for item in client.get("/api/brokers").json()]
    assert client.post("/api/brokers", json={"broker_name": "btg pactual"}).status_code == 409

    response = client.post(
        "/api/stocks",
        json={"stock_name": "ITUB4", "stock_quantity": 3, "stock_price": "35", "broker_id": broker["broker_id"], "trade_side": "BUY"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["broker_id"] == broker["broker_id"]
    assert response.json()["broker_name"] == "BTG Pactual"

    # Em uso por uma operação, a corretora não pode ser removida.
    assert client.delete(f"/api/brokers/{broker['broker_id']}").status_code == 409


def test_remover_corretora_sem_operacoes(client):
    broker_id = client.post("/api/brokers", json={"broker_name": "Genial"}).json()["broker_id"]

    assert client.delete(f"/api/brokers/{broker_id}").status_code == 200
    assert broker_id not in [item["broker_id"] for item in client.get("/api/brokers").json()]


def test_corretoras_exigem_usuario_autenticado(client):
    del main.app.dependency_overrides[get_current_user]

    assert client.get("/api/brokers").status_code == 401


def _trade(client, **changes):
    payload = dict(stock_name="PETR4", stock_quantity=10, stock_price="20.00",
                   broker_id=1, trade_side="BUY", trade_date="2026-09-01T10:00:00Z")
    payload.update(changes)
    response = client.post("/api/stocks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_cadastrar_corretora_e_utilizar_id_real(client, db, user, other_user):
    db.add(models.Broker(broker_id=101, broker_name="Corretora existente"))
    db.commit()
    response = client.post("/api/brokers", json={"broker_name": " Nova Corretora "})
    assert response.status_code == 201
    broker = response.json()
    assert broker["broker_name"] == "Nova Corretora"
    assert client.post("/api/brokers", json={"broker_name": "nova corretora"}).status_code == 409
    assert client.get("/api/brokers").json() == [broker]
    _trade(client, broker_id=broker["broker_id"], broker_source="registered")
    main.app.dependency_overrides[get_current_user] = lambda: other_user
    assert client.get("/api/brokers").json() == []
    denied = client.post("/api/stocks", json=dict(stock_name="PETR4", stock_quantity=1,
        stock_price="20", broker_id=broker["broker_id"], broker_source="registered", trade_side="BUY"))
    assert denied.status_code == 404
    assert client.post("/api/brokers", json={"broker_name": "Nova Corretora"}).status_code == 201


@pytest.mark.parametrize("payload", [{}, {"broker_name": " "}, {"broker_name": "x" * 151}])
def test_cadastrar_corretora_valida_campos(client, payload):
    assert client.post("/api/brokers", json=payload).status_code == 422
    assert client.get("/api/brokers").json() == []


def test_paginacao_preserva_totais_e_isolamento(client, other_user):
    _trade(client)
    _trade(client, stock_name="VALE3")
    first = client.get("/api/stocks/carteira/paginada", params={"limit": 1}).json()
    second = client.get("/api/stocks/carteira/paginada", params={"limit": 1, "page": 2}).json()
    assert first["results"][0]["stock_name"] == "PETR4"
    assert second["results"][0]["stock_name"] == "VALE3"
    assert first["total_items"] == second["total_items"] == 2
    assert first["total_quantity"] == 20
    assert float(first["total_invested"]) == 400
    assert client.get("/api/stocks/carteira/paginada?page=0").status_code == 422
    assert client.get("/api/stocks/carteira/paginada?limit=101").status_code == 422
    main.app.dependency_overrides[get_current_user] = lambda: other_user
    assert client.get("/api/stocks/carteira/paginada").json()["total_items"] == 0


def test_editar_movimentacao_recalcula_e_protege_historico(client, other_user):
    trade = _trade(client)
    _trade(client, trade_side="SELL", stock_quantity=5, trade_date="2026-09-02T10:00:00Z")
    url = "/api/stocks/PETR4/trades"
    params = {"trade_date": trade["trade_date"]}
    update = dict(stock_quantity=20, stock_price="30", trade_side="BUY")
    assert client.patch(url, params=params, json=update).status_code == 200
    position = client.get("/api/stocks/carteira").json()[0]
    assert position["stock_quantity"] == 15
    assert float(position["preco_medio"]) == 30
    assert client.patch(url, params=params, json={**update, "stock_quantity": 2}).status_code == 422
    assert client.get("/api/stocks/carteira").json()[0] == position
    main.app.dependency_overrides[get_current_user] = lambda: other_user
    assert client.patch(url, params=params, json=update).status_code == 404


def test_crud_rendimentos_e_isolamento(client, other_user, user):
    _trade(client)
    payload = dict(stock_name="petr4", amount="15.50", received_at="2026-09-02T12:00:00Z", kind="DIVIDEND")
    created = client.post("/api/incomes", json=payload)
    assert created.status_code == 201, created.text
    income_id = created.json()["income_id"]
    assert len(client.get("/api/incomes").json()) == 1
    url = f"/api/incomes/{income_id}"
    assert client.put(url, json={**payload, "amount": "21"}).status_code == 200
    assert float(client.get("/api/incomes").json()[0]["amount"]) == 21
    assert client.post("/api/incomes", json={**payload, "amount": 0}).status_code == 422
    assert client.post("/api/incomes", json={**payload, "stock_name": "VALE3"}).status_code == 404
    main.app.dependency_overrides[get_current_user] = lambda: other_user
    assert client.get("/api/incomes").json() == []
    assert client.put(url, json=payload).status_code == 404
    assert client.delete(url).status_code == 404
    main.app.dependency_overrides[get_current_user] = lambda: user
    assert client.delete(url).status_code == 204
    assert client.get("/api/incomes").json() == []


def test_mensagem_ativo_inexistente(client, monkeypatch):
    from src.services import market_data_service
    async def empty(*args, **kwargs):
        return {"results": []}
    monkeypatch.setattr(market_data_service, "_get", empty)
    main.app.dependency_overrides[get_market_data_service] = market_data_service.BrapiMarketDataService
    response = client.post("/api/stocks", json=dict(stock_name="INVALIDO", stock_quantity=1,
        stock_price="20", broker_id=1, trade_side="BUY"))
    assert response.status_code == 404
    assert response.json()["detail"] == "Tente novamente! Esse ativo não existe na B3."
    assert client.get("/api/stocks").json() == []


class FakeGoogle:
    """Substitui apenas o provedor externo; sessões e usuários são reais."""
    configured = True
    verified = True
    error = None
    def is_configured(self):
        return self.configured
    async def authorize_redirect(self, request, redirect_uri):
        from fastapi.responses import RedirectResponse
        request.session["oauth_test_started"] = True
        return RedirectResponse("https://accounts.google.com/test-authorize")
    async def authorize_access_token(self, request):
        from authlib.integrations.base_client.errors import OAuthError
        if self.error or not request.session.pop("oauth_test_started", False):
            raise OAuthError(error=self.error or "mismatching_state")
        return {"userinfo": {"email": "google@example.com", "name": "Google User", "email_verified": self.verified}}
    async def get_userinfo(self, token):
        return token["userinfo"]


def test_oauth_fluxo_completo_com_provedor_simulado(client, monkeypatch, db):
    from src.dependencies.components import get_google_oauth_service
    monkeypatch.delenv("FRONTEND_AUTH_CALLBACK_URL", raising=False)
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    main.app.dependency_overrides.pop(get_current_user)
    google = FakeGoogle()
    main.app.dependency_overrides[get_google_oauth_service] = lambda: google
    start = client.get("/api/v1/auth/google", follow_redirects=False)
    assert start.status_code == 307
    assert start.headers["location"].startswith("https://accounts.google.com/")
    callback = client.get("/api/v1/auth/google/callback")
    assert callback.status_code == 200, callback.text
    auth = callback.json()
    headers = {"Authorization": "Bearer " + auth["access_token"]}
    assert client.get("/api/v1/auth/me", headers=headers).json()["email"] == "google@example.com"
    assert db.query(models.RefreshToken).count() == 1
    assert client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": auth["refresh_token"]}).status_code == 200
    assert db.query(models.RefreshToken).count() == 0
    client.get("/api/v1/auth/google", follow_redirects=False)
    assert client.get("/api/v1/auth/google/callback").status_code == 200
    assert db.query(models.User).filter_by(email="google@example.com").count() == 1


@pytest.mark.parametrize("scenario,expected", [("unconfigured", 503), ("unverified", 401), ("denied", 401), ("state", 401)])
def test_oauth_erros_nao_criam_sessao(client, monkeypatch, db, scenario, expected):
    from src.dependencies.components import get_google_oauth_service
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    google = FakeGoogle()
    google.configured = scenario != "unconfigured"
    google.verified = scenario != "unverified"
    google.error = "access_denied" if scenario == "denied" else None
    main.app.dependency_overrides[get_google_oauth_service] = lambda: google
    if scenario != "state":
        client.get("/api/v1/auth/google", follow_redirects=False)
    response = client.get("/api/v1/auth/google/callback")
    assert response.status_code == expected
    assert db.query(models.RefreshToken).count() == 0
    assert db.query(models.User).filter_by(email="google@example.com").count() == 0
