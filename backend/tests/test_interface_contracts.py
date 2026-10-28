"""
Conformidade das implementações com as interfaces (Protocols) especificadas.

Garante que PortfolioService e InvestmentService fornecem todas as operações
de IPortfolioService e IInvestmentService com os mesmos parâmetros e o mesmo
modo de execução (síncrono/assíncrono).
"""

import inspect

import pytest

from src.interfaces import (
    IBrokerService,
    IInvestmentService,
    IMarketDataService,
    IPortfolioService,
    IReturnsService,
)
from src.services.broker_service import BrokerService
from src.services.investment_service import InvestmentService
from src.services.market_data_service import BrapiMarketDataService
from src.services.portfolio_service import PortfolioService
from src.services.returns_service import ReturnsService


def _operations(protocol) -> list[str]:
    return [
        name
        for name, member in vars(protocol).items()
        if callable(member) and not name.startswith("_")
    ]


@pytest.mark.parametrize(
    ("protocol", "implementation"),
    [
        (IPortfolioService, PortfolioService),
        (IInvestmentService, InvestmentService),
        (IMarketDataService, BrapiMarketDataService),
        (IReturnsService, ReturnsService),
        (IBrokerService, BrokerService),
    ],
    ids=["Portfolio", "Investment", "MarketData", "Returns", "Broker"],
)
def test_implementacao_fornece_todas_as_operacoes_da_interface(protocol, implementation):
    for name in _operations(protocol):
        expected = getattr(protocol, name)
        actual = getattr(implementation, name, None)

        assert actual is not None, f"{implementation.__name__} não implementa {name}()"
        assert list(inspect.signature(actual).parameters) == list(
            inspect.signature(expected).parameters
        ), f"Assinatura divergente em {name}()"
        assert inspect.iscoroutinefunction(actual) == inspect.iscoroutinefunction(expected)


def test_interfaces_expoem_as_operacoes_do_lab3():
    assert set(_operations(IPortfolioService)) >= {
        "create_portfolio",       # criarCarteira()
        "list_portfolios",        # consultarCarteira()
        "get_portfolio",          # consultarCarteira()
        "update_portfolio",       # editarCarteira()
        "delete_portfolio",       # removerCarteira()
        "associate_investment",   # associarInvestimento()
    }
    assert set(_operations(IInvestmentService)) >= {
        "create_trade",           # cadastrarAcao() / registrarMovimentacao()
        "list_trades",            # consultarInvestimentos()
        "get_positions",          # consultarInvestimentos()
        "associate_position",     # editarInvestimento()
        "remove_position",        # removerInvestimento()
    }


def test_investment_requer_portfolio_pelo_construtor():
    parameters = inspect.signature(InvestmentService.__init__).parameters

    assert parameters["portfolios"].annotation is IPortfolioService


def test_returns_requer_componentes_pelo_construtor():
    parameters = inspect.signature(ReturnsService.__init__).parameters

    assert parameters["investments"].annotation is IInvestmentService
    assert parameters["portfolios"].annotation is IPortfolioService
    assert parameters["market_data"].annotation is IMarketDataService
