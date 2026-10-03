"""Contratos consumidos entre os componentes atualmente implementados."""

from decimal import Decimal
from typing import Any, Protocol

from fastapi import Request
from fastapi.responses import RedirectResponse
from .. import models
from ..db.schemas import (
    AuthResponse,
    PositionOut,
    StockTradeCreate,
    UserCreate,
)


class IUserService(Protocol):
    """Operações fornecidas pelo componente de usuários."""

    def get_by_id(self, user_id: int) -> models.User | None: ...

    def get_by_email(self, email: str) -> models.User | None: ...

    def create(self, user_in: UserCreate) -> models.User: ...

    def create_from_google(self, name: str, email: str) -> models.User: ...


class IAuthService(Protocol):
    """Operações fornecidas pelo componente de autenticação."""

    def authenticate(self, email: str, password: str) -> AuthResponse: ...

    def issue_session(self, user: models.User) -> AuthResponse: ...

    def refresh_session(self, raw_refresh_token: str) -> AuthResponse: ...

    def logout(self, refresh_token: str, user_id: int) -> None: ...

    def logout_all(self, user_id: int) -> None: ...


class IGoogleOAuthService(Protocol):
    """Adaptador do provedor OAuth externo usado pelo componente Auth."""

    def is_configured(self) -> bool: ...

    async def authorize_redirect(
        self, request: Request, redirect_uri: str
    ) -> RedirectResponse: ...

    async def authorize_access_token(self, request: Request) -> dict[str, Any]: ...

    async def get_userinfo(self, token: dict[str, Any]) -> dict[str, Any]: ...


class IMarketDataService(Protocol):
    """Operações de consulta de ativos e preços do componente Market Data."""

    async def validate_ticker(self, stock_name: str) -> dict[str, Any]: ...

    async def get_quote(self, stock_name: str) -> Decimal: ...

    async def list_tickers(
        self,
        search: str | None = None,
        tipo: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]: ...

    async def autocomplete_tickers(self, query: str, limit: int = 8) -> list[dict[str, str]]: ...


class IInvestmentService(Protocol):
    """Operações atualmente fornecidas pelo componente de investimentos."""

    async def create_trade(
        self, user_id: int, trade_in: StockTradeCreate
    ) -> models.UserStock: ...

    def list_trades(self, user_id: int) -> list[models.UserStock]: ...

    def get_positions(self, user_id: int) -> list[PositionOut]: ...
