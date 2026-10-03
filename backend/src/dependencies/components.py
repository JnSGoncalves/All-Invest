"""Provedores de implementação para os contratos entre componentes."""

from fastapi import Depends
from sqlalchemy.orm import Session

from ..interfaces import (
    IAuthService,
    IGoogleOAuthService,
    IInvestmentService,
    IMarketDataService,
    IUserService,
)
from ..db.database import get_db
from ..services.auth_service import AuthService
from ..services.google.oauth_service import GoogleOAuthService
from ..services.investment_service import InvestmentService
from ..services.market_data_service import BrapiMarketDataService
from ..services.user_service import UserService


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


def get_investment_service(
    db: Session = Depends(get_db),
    market_data: IMarketDataService = Depends(get_market_data_service),
) -> IInvestmentService:
    return InvestmentService(db, market_data)
