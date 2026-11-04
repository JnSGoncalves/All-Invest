"""Interfaces públicas entre os componentes existentes da API."""

from .components import (
    IAuthService,
    IBrokerService,
    IIncomeService,
    IGoogleOAuthService,
    IInvestmentService,
    IMarketDataService,
    IPerformanceService,
    IPortfolioService,
    IReportService,
    IReturnsService,
    IUserService,
)

__all__ = [
    "IAuthService",
    "IBrokerService",
    "IIncomeService",
    "IGoogleOAuthService",
    "IInvestmentService",
    "IMarketDataService",
    "IPerformanceService",
    "IPortfolioService",
    "IReportService",
    "IReturnsService",
    "IUserService",
]
