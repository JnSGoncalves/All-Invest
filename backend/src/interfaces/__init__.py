"""Interfaces públicas entre os componentes existentes da API."""

from .components import (
    IAuthService,
    IGoogleOAuthService,
    IInvestmentService,
    IMarketDataService,
    IUserService,
)

__all__ = [
    "IAuthService",
    "IGoogleOAuthService",
    "IInvestmentService",
    "IMarketDataService",
    "IUserService",
]
