"""Interfaces públicas entre os componentes existentes da API."""

from .components import (
    IAuthService,
    IBrokerService,
    IIncomeService,
    IGoogleOAuthService,
    IInvestmentService,
    IMarketDataService,
    IPortfolioService,
    IUserService,
)

__all__ = [
    "IAuthService",
    "IBrokerService",
    "IIncomeService",
    "IGoogleOAuthService",
    "IInvestmentService",
    "IMarketDataService",
    "IPortfolioService",
    "IUserService",
]
