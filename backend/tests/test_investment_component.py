"""
Testes unitários do Investment Component (operações de IInvestmentService).

O Portfolio Component é substituído por um stub que implementa
IPortfolioService, isolando a lógica de investimentos.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from src.db.schemas import StockTradeCreate
from src.services.investment_service import InvestmentService

pytestmark = pytest.mark.anyio

T0 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


class StubPortfolioService:
    """Stub de IPortfolioService: só a carteira 7 existe para o usuário."""

    def __init__(self) -> None:
        self.portfolio = SimpleNamespace(portfolio_id=7, portfolio_name="Dividendos")
        self.associations: dict[int, SimpleNamespace] = {}
        self.calls: list[tuple] = []

    def get_portfolio(self, user_id, portfolio_id):
        self.calls.append(("get_portfolio", user_id, portfolio_id))
        if portfolio_id != self.portfolio.portfolio_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carteira não encontrada.")
        return self.portfolio

    def associate_investment(self, user_id, portfolio_id, stock_id):
        self.calls.append(("associate_investment", user_id, portfolio_id, stock_id))
        portfolio = self.get_portfolio(user_id, portfolio_id)
        self.associations[stock_id] = portfolio
        return portfolio

    def dissociate_investment(self, user_id, stock_id):
        self.calls.append(("dissociate_investment", user_id, stock_id))
        return self.associations.pop(stock_id, None) is not None

    def get_investment_portfolios(self, user_id):
        return dict(self.associations)

    # Operações de IPortfolioService não usadas pelo Investment Component.
    def create_portfolio(self, user_id, portfolio_in): raise NotImplementedError
    def list_portfolios(self, user_id): raise NotImplementedError
    def update_portfolio(self, user_id, portfolio_id, portfolio_in): raise NotImplementedError
    def delete_portfolio(self, user_id, portfolio_id): raise NotImplementedError


@pytest.fixture
def stub_portfolios():
    return StubPortfolioService()


@pytest.fixture
def service(db, market_data, stub_portfolios):
    return InvestmentService(db, market_data, stub_portfolios)


def trade(stock_name="PETR4", qty=10, price="20.00", side="BUY", minutes=0, **extra):
    return StockTradeCreate(
        stock_name=stock_name,
        stock_quantity=qty,
        stock_price=Decimal(price) if price is not None else None,
        broker_id=1,
        trade_side=side,
        trade_date=T0 + timedelta(minutes=minutes),
        **extra,
    )


# --- create_trade (registrarMovimentacao / cadastrarAcao) -------------------

async def test_create_trade_valida_ticker_e_persiste_compra(service, market_data, user):
    created = await service.create_trade(user.user_id, trade(stock_name="petr4"))

    assert ("validate_ticker", "PETR4") in market_data.calls
    assert created.stock.stock_name == "PETR4"
    assert created.stock.company_name.startswith("Petróleo")
    assert created.broker.broker_name == "XP Investimentos"
    assert created.stock_quantity == 10


async def test_create_trade_com_auto_cotacao_usa_preco_do_market_data(service, market_data, user):
    created = await service.create_trade(
        user.user_id, trade(price=None, auto_cotacao=True)
    )

    assert ("get_quote", "PETR4") in market_data.calls
    assert created.stock_price == Decimal("38.50")


async def test_create_trade_ticker_inexistente_retorna_404(service, user):
    with pytest.raises(HTTPException) as exc:
        await service.create_trade(user.user_id, trade(stock_name="XXXX3"))

    assert exc.value.status_code == 404
    assert service.list_trades(user.user_id) == []


async def test_create_trade_corretora_inexistente_retorna_400(service, user):
    payload = trade().model_copy(update={"broker_id": 99})

    with pytest.raises(HTTPException) as exc:
        await service.create_trade(user.user_id, payload)

    assert exc.value.status_code == 400


async def test_create_trade_venda_acima_do_saldo_retorna_422(service, user):
    await service.create_trade(user.user_id, trade(qty=5))

    with pytest.raises(HTTPException) as exc:
        await service.create_trade(user.user_id, trade(qty=6, side="SELL", minutes=1))

    assert exc.value.status_code == 422
    assert len(service.list_trades(user.user_id)) == 1


async def test_create_trade_com_carteira_valida_e_associa(service, stub_portfolios, user):
    created = await service.create_trade(user.user_id, trade(portfolio_id=7))

    assert ("get_portfolio", user.user_id, 7) in stub_portfolios.calls
    assert ("associate_investment", user.user_id, 7, created.stock_id) in stub_portfolios.calls


async def test_create_trade_com_carteira_inexistente_nao_grava_operacao(
    service, stub_portfolios, market_data, user
):
    with pytest.raises(HTTPException) as exc:
        await service.create_trade(user.user_id, trade(portfolio_id=99))

    assert exc.value.status_code == 404
    assert service.list_trades(user.user_id) == []
    assert market_data.calls == []  # validou a carteira antes de chamar a B3


# --- get_positions (consultarInvestimentos) ---------------------------------

async def test_get_positions_calcula_quantidade_e_preco_medio(service, user):
    await service.create_trade(user.user_id, trade(qty=10, price="20.00"))
    await service.create_trade(user.user_id, trade(qty=10, price="30.00", minutes=1))
    await service.create_trade(user.user_id, trade(qty=5, side="SELL", price="40.00", minutes=2))

    [position] = service.get_positions(user.user_id)

    assert position.stock_name == "PETR4"
    assert position.stock_quantity == 15
    assert position.preco_medio == Decimal("25.0000")
    assert position.portfolio_id is None


async def test_get_positions_oculta_ativo_zerado(service, user):
    await service.create_trade(user.user_id, trade(qty=10))
    await service.create_trade(user.user_id, trade(qty=10, side="SELL", minutes=1))

    assert service.get_positions(user.user_id) == []


async def test_get_positions_isola_usuarios(service, user, other_user):
    await service.create_trade(other_user.user_id, trade())

    assert service.get_positions(user.user_id) == []


async def test_get_positions_filtra_por_carteira(service, user):
    await service.create_trade(user.user_id, trade(stock_name="PETR4", portfolio_id=7))
    await service.create_trade(user.user_id, trade(stock_name="VALE3", minutes=1))

    names = [p.stock_name for p in service.get_positions(user.user_id, portfolio_id=7)]

    assert names == ["PETR4"]


# --- associate_position (editarInvestimento) --------------------------------

async def test_associate_position_retorna_posicao_com_carteira(service, user):
    await service.create_trade(user.user_id, trade())

    position = service.associate_position(user.user_id, "petr4", 7)

    assert position.portfolio_id == 7
    assert position.portfolio_name == "Dividendos"


async def test_associate_position_sem_posicao_retorna_404(service, stub_portfolios, user):
    with pytest.raises(HTTPException) as exc:
        service.associate_position(user.user_id, "PETR4", 7)

    assert exc.value.status_code == 404
    assert not any(call[0] == "associate_investment" for call in stub_portfolios.calls)


# --- remove_position (removerInvestimento) ----------------------------------

async def test_remove_position_apaga_operacoes_e_desassocia(service, stub_portfolios, user):
    created = await service.create_trade(user.user_id, trade(portfolio_id=7))
    stock_id = created.stock_id
    await service.create_trade(user.user_id, trade(minutes=1))

    deleted = service.remove_position(user.user_id, "petr4")

    assert deleted == 2
    assert service.list_trades(user.user_id) == []
    assert ("dissociate_investment", user.user_id, stock_id) in stub_portfolios.calls


async def test_remove_position_inexistente_retorna_404(service, user):
    with pytest.raises(HTTPException) as exc:
        service.remove_position(user.user_id, "PETR4")

    assert exc.value.status_code == 404
