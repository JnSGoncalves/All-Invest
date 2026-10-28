"""Interfaces públicas entre os componentes existentes da API."""

from .components import (
    IAuthService,
    IBrokerService,
    IGoogleOAuthService,
    IInvestmentService,
    IMarketDataService,
    IPortfolioService,
    IReturnsService,
    IUserService,
)

__all__ = [
    "IAuthService",
    "IBrokerService",
    "IGoogleOAuthService",
    "IInvestmentService",
    "IMarketDataService",
    "IPortfolioService",
    "IReturnsService",
    "IUserService",
]
