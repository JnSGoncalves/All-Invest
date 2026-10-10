"""
Conformidade das implementações com as interfaces (Protocols) especificadas.

Garante que PortfolioService e InvestmentService fornecem todas as operações
de IPortfolioService e IInvestmentService com os mesmos parâmetros e o mesmo
modo de execução (síncrono/assíncrono).
"""

import inspect

import pytest

from src.interfaces import IInvestmentService, IPortfolioService
from src.services.investment_service import InvestmentService
from src.services.portfolio_service import PortfolioService


def _operations(protocol) -> list[str]:
    return [
        name
        for name, member in vars(protocol).items()
        if callable(member) and not name.startswith("_")
    ]


@pytest.mark.parametrize(
    ("protocol", "implementation"),
    [(IPortfolioService, PortfolioService), (IInvestmentService, InvestmentService)],
    ids=["Portfolio", "Investment"],
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
