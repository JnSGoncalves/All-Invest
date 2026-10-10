"""
Testes de integração: Investment Component <-> Portfolio Component.

Ambos os componentes são as implementações reais, ligadas pela interface
IPortfolioService (fixture `investment_service` em conftest.py) e
compartilhando o mesmo banco. Apenas o Market Data externo é simulado.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from src.db.schemas import PortfolioCreate, StockTradeCreate

pytestmark = pytest.mark.anyio

T0 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


def trade(stock_name="PETR4", qty=10, side="BUY", minutes=0, portfolio_id=None):
    return StockTradeCreate(
        stock_name=stock_name,
        stock_quantity=qty,
        stock_price=Decimal("20.00"),
        broker_id=2,
        trade_side=side,
        trade_date=T0 + timedelta(minutes=minutes),
        portfolio_id=portfolio_id,
    )


@pytest.fixture
def dividendos(portfolio_service, user):
    return portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Dividendos"))


@pytest.fixture
def trade_portfolio(portfolio_service, user):
    return portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))


async def test_registrar_operacao_com_carteira_associa_ativo_no_portfolio(
    investment_service, portfolio_service, user, dividendos
):
    created = await investment_service.create_trade(
        user.user_id, trade(portfolio_id=dividendos.portfolio_id)
    )

    associations = portfolio_service.get_investment_portfolios(user.user_id)
    assert associations[created.stock_id].portfolio_id == dividendos.portfolio_id

    [position] = investment_service.get_positions(user.user_id)
    assert position.portfolio_name == "Dividendos"


async def test_associar_posicao_existente_e_mover_entre_carteiras(
    investment_service, user, dividendos, trade_portfolio
):
    await investment_service.create_trade(user.user_id, trade())

    first = investment_service.associate_position(user.user_id, "PETR4", dividendos.portfolio_id)
    moved = investment_service.associate_position(user.user_id, "PETR4", trade_portfolio.portfolio_id)

    assert first.portfolio_name == "Dividendos"
    assert moved.portfolio_name == "Trade"
    assert investment_service.get_positions(user.user_id, dividendos.portfolio_id) == []


async def test_consultar_posicoes_por_carteira(
    investment_service, user, dividendos, trade_portfolio
):
    await investment_service.create_trade(user.user_id, trade("PETR4", portfolio_id=dividendos.portfolio_id))
    await investment_service.create_trade(user.user_id, trade("VALE3", minutes=1, portfolio_id=trade_portfolio.portfolio_id))
    await investment_service.create_trade(user.user_id, trade("ITUB4", minutes=2))

    por_carteira = {
        p.stock_name: p.portfolio_name for p in investment_service.get_positions(user.user_id)
    }
    somente_dividendos = investment_service.get_positions(user.user_id, dividendos.portfolio_id)

    assert por_carteira == {"PETR4": "Dividendos", "VALE3": "Trade", "ITUB4": None}
    assert [p.stock_name for p in somente_dividendos] == ["PETR4"]


async def test_remover_carteira_preserva_operacoes_e_desassocia_posicoes(
    investment_service, portfolio_service, user, dividendos
):
    await investment_service.create_trade(user.user_id, trade(portfolio_id=dividendos.portfolio_id))

    portfolio_service.delete_portfolio(user.user_id, dividendos.portfolio_id)

    [position] = investment_service.get_positions(user.user_id)
    assert position.stock_quantity == 10
    assert position.portfolio_id is None
    assert len(investment_service.list_trades(user.user_id)) == 1


async def test_remover_investimento_remove_associacao_no_portfolio(
    investment_service, portfolio_service, user, dividendos
):
    await investment_service.create_trade(user.user_id, trade(portfolio_id=dividendos.portfolio_id))

    investment_service.remove_position(user.user_id, "PETR4")

    assert portfolio_service.get_investment_portfolios(user.user_id) == {}


async def test_nao_associa_ativo_a_carteira_de_outro_usuario(
    investment_service, portfolio_service, user, other_user
):
    alheia = portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Alheia"))
    await investment_service.create_trade(user.user_id, trade())

    with pytest.raises(HTTPException) as exc:
        investment_service.associate_position(user.user_id, "PETR4", alheia.portfolio_id)

    assert exc.value.status_code == 404
    assert portfolio_service.get_investment_portfolios(user.user_id) == {}
    assert portfolio_service.get_investment_portfolios(other_user.user_id) == {}


async def test_filtrar_por_carteira_inexistente_retorna_404(investment_service, user):
    with pytest.raises(HTTPException) as exc:
        investment_service.get_positions(user.user_id, portfolio_id=123)

    assert exc.value.status_code == 404
