"""Implementação do Portfolio Component: carteiras do usuário e associação de ativos."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_portfolio(
        self, user_id: int, portfolio_in: schemas.PortfolioCreate
    ) -> models.Portfolio:
        self._ensure_name_available(user_id, portfolio_in.portfolio_name)
        try:
            return crud.create_portfolio(
                self._db,
                user_id=user_id,
                portfolio_name=portfolio_in.portfolio_name,
                description=portfolio_in.description,
            )
        except IntegrityError as exc:
            self._db.rollback()
            raise self._duplicated_name() from exc

    def list_portfolios(self, user_id: int) -> list[models.Portfolio]:
        return crud.list_portfolios(self._db, user_id)

    def get_portfolio(self, user_id: int, portfolio_id: int) -> models.Portfolio:
        portfolio = crud.get_portfolio(
            self._db, user_id=user_id, portfolio_id=portfolio_id
        )
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carteira não encontrada.",
            )
        return portfolio

    def update_portfolio(
        self, user_id: int, portfolio_id: int, portfolio_in: schemas.PortfolioUpdate
    ) -> models.Portfolio:
        portfolio = self.get_portfolio(user_id, portfolio_id)
        changes = portfolio_in.model_dump(exclude_unset=True)

        new_name = changes.get("portfolio_name")
        if new_name and new_name.lower() != portfolio.portfolio_name.lower():
            self._ensure_name_available(user_id, new_name)

        try:
            return crud.update_portfolio(self._db, portfolio, changes)
        except IntegrityError as exc:
            self._db.rollback()
            raise self._duplicated_name() from exc

    def delete_portfolio(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self.get_portfolio(user_id, portfolio_id)
        crud.delete_portfolio(self._db, portfolio)

    def associate_investment(
        self, user_id: int, portfolio_id: int, stock_id: int
    ) -> models.Portfolio:
        portfolio = self.get_portfolio(user_id, portfolio_id)
        crud.set_stock_portfolio(
            self._db,
            user_id=user_id,
            stock_id=stock_id,
            portfolio_id=portfolio.portfolio_id,
        )
        return portfolio

    def dissociate_investment(self, user_id: int, stock_id: int) -> bool:
        return crud.delete_stock_portfolio(
            self._db, user_id=user_id, stock_id=stock_id
        )

    def get_investment_portfolios(self, user_id: int) -> dict[int, models.Portfolio]:
        return crud.get_stock_portfolios(self._db, user_id)

    def _ensure_name_available(self, user_id: int, portfolio_name: str) -> None:
        if crud.get_portfolio_by_name(
            self._db, user_id=user_id, portfolio_name=portfolio_name
        ):
            raise self._duplicated_name()

    @staticmethod
    def _duplicated_name() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Você já possui uma carteira com este nome.",
        )
