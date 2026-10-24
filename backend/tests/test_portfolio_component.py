"""Testes unitários do Portfolio Component (operações de IPortfolioService)."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src import models
from src.db.schemas import PortfolioCreate, PortfolioUpdate


def _stock(db, ticker: str = "PETR4") -> models.Stock:
    stock = models.Stock(stock_name=ticker, company_name=f"Empresa {ticker}")
    db.add(stock)
    db.commit()
    return stock


# --- create_portfolio (criarCarteira) ---------------------------------------

def test_create_portfolio_persiste_carteira_do_usuario(portfolio_service, user):
    portfolio = portfolio_service.create_portfolio(
        user.user_id,
        PortfolioCreate(portfolio_name="  Dividendos  ", description="Renda passiva"),
    )

    assert portfolio.portfolio_id is not None
    assert portfolio.user_id == user.user_id
    assert portfolio.portfolio_name == "Dividendos"
    assert portfolio.description == "Renda passiva"


def test_create_portfolio_rejeita_nome_repetido_sem_diferenciar_maiusculas(
    portfolio_service, user
):
    portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Longo Prazo"))

    with pytest.raises(HTTPException) as exc:
        portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="longo prazo"))

    assert exc.value.status_code == 409


def test_create_portfolio_permite_mesmo_nome_para_usuarios_diferentes(
    portfolio_service, user, other_user
):
    first = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))
    second = portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Trade"))

    assert first.portfolio_id != second.portfolio_id


def test_portfolio_create_rejeita_nome_vazio():
    with pytest.raises(ValidationError):
        PortfolioCreate(portfolio_name="   ")


# --- list_portfolios / get_portfolio (consultarCarteira) --------------------

def test_list_portfolios_retorna_somente_as_do_usuario_ordenadas(
    portfolio_service, user, other_user
):
    portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))
    portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Aposentadoria"))
    portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Alheia"))

    names = [p.portfolio_name for p in portfolio_service.list_portfolios(user.user_id)]

    assert names == ["Aposentadoria", "Trade"]


def test_get_portfolio_de_outro_usuario_retorna_404(portfolio_service, user, other_user):
    alheia = portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Alheia"))

    with pytest.raises(HTTPException) as exc:
        portfolio_service.get_portfolio(user.user_id, alheia.portfolio_id)

    assert exc.value.status_code == 404


# --- update_portfolio (editarCarteira) --------------------------------------

def test_update_portfolio_altera_somente_campos_enviados(portfolio_service, user):
    portfolio = portfolio_service.create_portfolio(
        user.user_id, PortfolioCreate(portfolio_name="Trade", description="Curto prazo")
    )

    updated = portfolio_service.update_portfolio(
        user.user_id, portfolio.portfolio_id, PortfolioUpdate(portfolio_name="Swing Trade")
    )

    assert updated.portfolio_name == "Swing Trade"
    assert updated.description == "Curto prazo"


def test_update_portfolio_rejeita_nome_de_outra_carteira(portfolio_service, user):
    portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Dividendos"))
    trade = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))

    with pytest.raises(HTTPException) as exc:
        portfolio_service.update_portfolio(
            user.user_id, trade.portfolio_id, PortfolioUpdate(portfolio_name="DIVIDENDOS")
        )

    assert exc.value.status_code == 409


def test_portfolio_update_exige_ao_menos_um_campo():
    with pytest.raises(ValidationError):
        PortfolioUpdate()


# --- delete_portfolio (removerCarteira) -------------------------------------

def test_delete_portfolio_remove_carteira_e_associacoes(portfolio_service, db, user):
    portfolio = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))
    stock = _stock(db)
    portfolio_service.associate_investment(user.user_id, portfolio.portfolio_id, stock.stock_id)

    portfolio_service.delete_portfolio(user.user_id, portfolio.portfolio_id)

    with pytest.raises(HTTPException) as exc:
        portfolio_service.get_portfolio(user.user_id, portfolio.portfolio_id)
    assert exc.value.status_code == 404
    assert portfolio_service.get_investment_portfolios(user.user_id) == {}


def test_delete_portfolio_de_outro_usuario_retorna_404(portfolio_service, user, other_user):
    alheia = portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Alheia"))

    with pytest.raises(HTTPException) as exc:
        portfolio_service.delete_portfolio(user.user_id, alheia.portfolio_id)

    assert exc.value.status_code == 404
    assert portfolio_service.get_portfolio(other_user.user_id, alheia.portfolio_id)


# --- associate / dissociate (associarInvestimento) --------------------------

def test_associate_investment_associa_e_move_entre_carteiras(portfolio_service, db, user):
    trade = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))
    longo = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Longo"))
    stock = _stock(db)

    portfolio_service.associate_investment(user.user_id, trade.portfolio_id, stock.stock_id)
    portfolio_service.associate_investment(user.user_id, longo.portfolio_id, stock.stock_id)

    associations = portfolio_service.get_investment_portfolios(user.user_id)
    assert {k: v.portfolio_name for k, v in associations.items()} == {stock.stock_id: "Longo"}


def test_associate_investment_em_carteira_de_outro_usuario_retorna_404(
    portfolio_service, db, user, other_user
):
    alheia = portfolio_service.create_portfolio(other_user.user_id, PortfolioCreate(portfolio_name="Alheia"))
    stock = _stock(db)

    with pytest.raises(HTTPException) as exc:
        portfolio_service.associate_investment(user.user_id, alheia.portfolio_id, stock.stock_id)

    assert exc.value.status_code == 404
    assert portfolio_service.get_investment_portfolios(user.user_id) == {}


def test_dissociate_investment_informa_se_havia_associacao(portfolio_service, db, user):
    portfolio = portfolio_service.create_portfolio(user.user_id, PortfolioCreate(portfolio_name="Trade"))
    stock = _stock(db)
    portfolio_service.associate_investment(user.user_id, portfolio.portfolio_id, stock.stock_id)

    assert portfolio_service.dissociate_investment(user.user_id, stock.stock_id) is True
    assert portfolio_service.dissociate_investment(user.user_id, stock.stock_id) is False
