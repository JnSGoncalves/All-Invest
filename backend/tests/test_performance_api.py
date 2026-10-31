import pytest

from src import main
from src.dependencies.auth import get_current_user
from tests.test_api_integration import client, _trade  # Fixture HTTP compartilhada.


def test_rendimento_fluxo_http_e_isolamento(client, other_user):
    _trade(client)
    response = client.get("/api/stocks/rendimentos?start=2026-09-01&end=2026-09-30")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["has_assets"]
    assert float(result["gain"]) == 185  # 10 * 38,50 - 10 * 20.
    assert result["assets"][0]["stock_name"] == "PETR4"
    main.app.dependency_overrides[get_current_user] = lambda: other_user
    empty = client.get("/api/stocks/rendimentos?start=2026-09-01&end=2026-09-30").json()
    assert not empty["has_assets"]
    assert empty["assets"] == []


@pytest.mark.parametrize("query", ["", "?start=errado&end=2026-09-30", "?start=2026-09-30&end=2026-09-01", "?start=2026-09-01&end=2999-01-01"])
def test_validacao_periodo_http(client, query):
    assert client.get("/api/stocks/rendimentos" + query).status_code == 422


def test_rendimento_exige_api_key_e_sessao(client):
    url = "/api/stocks/rendimentos?start=2026-09-01&end=2026-09-30"
    assert client.get(url, headers={"X-API-Key": "invalida"}).status_code == 401
    main.app.dependency_overrides.pop(get_current_user)
    assert client.get(url).status_code == 401
