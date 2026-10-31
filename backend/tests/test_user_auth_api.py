import pytest
from datetime import timedelta

from src import models
from src.services import security
from tests.test_api_integration import client


def test_cadastro_persiste_hash_login_e_conta_duplicada(client, db):
    payload = {"name": "  Pessoa Teste  ", "email": "pessoa@example.com", "password": "UmaSenha123"}
    created = client.post("/api/users", json=payload)
    assert created.status_code == 201
    assert created.json()["name"] == "Pessoa Teste"
    assert "password_hash" not in created.json()
    saved = db.query(models.User).filter_by(email=payload["email"]).one()
    assert saved.password_hash != payload["password"]
    assert security.verify_password(payload["password"], saved.password_hash)
    assert client.post("/api/users", json=payload).status_code == 409
    auth = client.post("/api/v1/auth/login", json=payload)
    assert auth.status_code == 200
    assert auth.json()["user"]["user_id"] == saved.user_id
    assert len(auth.json()["refresh_token"]) >= 32
    assert client.post("/api/v1/auth/login", json={**payload, "password": "outra"}).status_code == 401


@pytest.mark.parametrize("field,value", [("name", " "), ("email", "errado"), ("password", "123"), ("password", "é" * 40)])
def test_cadastro_invalido_nao_persiste(client, db, field, value):
    payload = {"name": "Pessoa", "email": "nova@example.com", "password": "UmaSenha123", field: value}
    count = db.query(models.User).count()
    assert client.post("/api/users", json=payload).status_code == 422
    assert db.query(models.User).count() == count


def test_login_inexistente_sugere_cadastro(client):
    response = client.post("/api/v1/auth/login", json={"email": "inexistente@example.com", "password": "UmaSenha123"})
    assert response.status_code == 404
    assert "cadastrar" in response.json()["detail"]


@pytest.mark.parametrize("expired", [False, True])
def test_renovacao_da_sessao_persistida_em_utc(client, db, expired):
    payload = {"name": "Pessoa", "email": "refresh@example.com", "password": "UmaSenha123"}
    assert client.post("/api/users", json=payload).status_code == 201
    auth = client.post("/api/v1/auth/login", json=payload).json()
    if expired:
        token = db.query(models.RefreshToken).one()
        token.expire_at = security.utc_now() - timedelta(seconds=1)
        db.commit()
    db.expunge_all()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]})
    assert response.status_code == (401 if expired else 200)
    if not expired:
        assert response.json()["refresh_token"] != auth["refresh_token"]
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]}).status_code == 401
