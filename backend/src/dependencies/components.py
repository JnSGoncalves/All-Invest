"""Provedores de implementação para os contratos entre componentes."""

from fastapi import Depends
from sqlalchemy.orm import Session

from ..interfaces import (
    IAuthService,
    IGoogleOAuthService,
    IInvestmentService,
    IMarketDataService,
    IPortfolioService,
    IUserService,
)
from ..db.database import get_db
from ..services.auth_service import AuthService
from ..services.google.oauth_service import GoogleOAuthService
from ..services.investment_service import InvestmentService
from ..services.market_data_service import BrapiMarketDataService
from ..services.portfolio_service import PortfolioService
from ..services.user_service import UserService
from ..interfaces.components import IBrokerService, IIncomeService, IPerformanceService
from ..services.performance_service import PerformanceService
from ..services.broker_service import BrokerService
from ..services.income_service import IncomeService


def get_user_service(db: Session = Depends(get_db)) -> IUserService:
    return UserService(db)


def get_auth_service(
    db: Session = Depends(get_db),
    users: IUserService = Depends(get_user_service),
) -> IAuthService:
    return AuthService(db, users)


def get_google_oauth_service() -> IGoogleOAuthService:
    return GoogleOAuthService()


def get_market_data_service() -> IMarketDataService:
    return BrapiMarketDataService()


def get_portfolio_service(db: Session = Depends(get_db)) -> IPortfolioService:
    return PortfolioService(db)


def get_investment_service(
    db: Session = Depends(get_db),
    market_data: IMarketDataService = Depends(get_market_data_service),
    portfolios: IPortfolioService = Depends(get_portfolio_service),
) -> IInvestmentService:
    # O Investment Component recebe o Portfolio Component somente pela interface.
    return InvestmentService(db, market_data, portfolios)


def get_broker_service(db: Session = Depends(get_db)) -> IBrokerService:
    return BrokerService(db)


def get_income_service(db: Session = Depends(get_db)) -> IIncomeService:
    return IncomeService(db)


def get_performance_service(
    db: Session = Depends(get_db),
    market_data: IMarketDataService = Depends(get_market_data_service),
) -> IPerformanceService:
    return PerformanceService(db, market_data)
