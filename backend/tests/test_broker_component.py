"""Testes unitários do Broker Component (operações de IBrokerService)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src import models
from src.db.schemas import BrokerCreate, StockTradeCreate


# --- list_brokers / get_broker (consultarCorretoras) ------------------------

def test_list_brokers_retorna_catalogo_em_ordem_alfabetica(broker_service):
    names = [broker.broker_name for broker in broker_service.list_brokers()]

    assert names == ["Clear", "NuInvest", "Rico", "XP Investimentos"]


def test_get_broker_inexistente_retorna_404(broker_service):
    with pytest.raises(HTTPException) as exc:
        broker_service.get_broker(99)

    assert exc.value.status_code == 404


# --- create_broker (cadastrarCorretora) -------------------------------------

def test_create_broker_normaliza_espacos_e_fica_no_catalogo(broker_service):
    broker = broker_service.create_broker(BrokerCreate(broker_name="  BTG   Pactual "))

    assert broker.broker_id is not None
    assert broker.broker_name == "BTG Pactual"
    assert broker in broker_service.list_brokers()


def test_create_broker_rejeita_nome_repetido_sem_diferenciar_maiusculas(broker_service):
    with pytest.raises(HTTPException) as exc:
        broker_service.create_broker(BrokerCreate(broker_name="rico"))

    assert exc.value.status_code == 409


def test_broker_create_rejeita_nome_vazio():
    with pytest.raises(ValidationError):
        BrokerCreate(broker_name="   ")


@pytest.mark.anyio
async def test_corretora_cadastrada_fica_disponivel_para_operacoes(
    broker_service, investment_service, user, other_user
):
    broker = broker_service.create_broker(BrokerCreate(broker_name="Inter"))

    # Catálogo global: qualquer usuário pode operar pela corretora recém-criada.
    for owner in (user, other_user):
        trade = await investment_service.create_trade(
            owner.user_id,
            StockTradeCreate(
                stock_name="VALE3",
                stock_quantity=5,
                stock_price=Decimal("60"),
                broker_id=broker.broker_id,
                trade_side="BUY",
            ),
        )
        assert trade.broker.broker_name == "Inter"


# --- delete_broker (removerCorretora) ---------------------------------------

def test_delete_broker_sem_operacoes_remove_do_catalogo(db, broker_service, user):
    broker = broker_service.create_broker(BrokerCreate(broker_name="Modal"))
    db.add(models.UserBroker(broker_id=broker.broker_id, user_id=user.user_id))
    db.commit()
    broker_id = broker.broker_id

    broker_service.delete_broker(broker_id)

    assert db.get(models.Broker, broker_id) is None
    assert db.get(models.UserBroker, (broker_id, user.user_id)) is None


@pytest.mark.anyio
async def test_delete_broker_com_operacoes_retorna_409(broker_service, investment_service, user):
    await investment_service.create_trade(
        user.user_id,
        StockTradeCreate(
            stock_name="PETR4",
            stock_quantity=10,
            stock_price=Decimal("30"),
            broker_id=1,
            trade_side="BUY",
            trade_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )

    with pytest.raises(HTTPException) as exc:
        broker_service.delete_broker(1)

    assert exc.value.status_code == 409
    assert broker_service.get_broker(1).broker_name == "XP Investimentos"


def test_delete_broker_inexistente_retorna_404(broker_service):
    with pytest.raises(HTTPException) as exc:
        broker_service.delete_broker(99)

    assert exc.value.status_code == 404
