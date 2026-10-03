"""Contratos consumidos entre os componentes atualmente implementados."""

from decimal import Decimal
from typing import Any, Protocol

from fastapi import Request
from fastapi.responses import RedirectResponse
from .. import models
from ..db.schemas import (
    AuthResponse,
    PortfolioCreate,
    PortfolioUpdate,
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


class IPortfolioService(Protocol):
    """
    Interface fornecida pelo Portfolio Component (Lab 3: IPortfolioService).

    Toda operação recebe o `user_id` autenticado; uma carteira de outro
    usuário é tratada como inexistente (HTTP 404).
    """

    def create_portfolio(
        self, user_id: int, portfolio_in: PortfolioCreate
    ) -> models.Portfolio:
        """criarCarteira. Pré: nome não usado pelo usuário (senão 409).
        Pós: carteira persistida e vinculada ao usuário."""
        ...

    def list_portfolios(self, user_id: int) -> list[models.Portfolio]:
        """consultarCarteira (lista). Pós: somente carteiras do usuário, por nome."""
        ...

    def get_portfolio(self, user_id: int, portfolio_id: int) -> models.Portfolio:
        """consultarCarteira (detalhe). Pré: carteira pertence ao usuário (senão 404)."""
        ...

    def update_portfolio(
        self, user_id: int, portfolio_id: int, portfolio_in: PortfolioUpdate
    ) -> models.Portfolio:
        """editarCarteira. Pré: carteira do usuário; novo nome livre (senão 409).
        Pós: somente os campos enviados são alterados."""
        ...

    def delete_portfolio(self, user_id: int, portfolio_id: int) -> None:
        """removerCarteira. Pré: carteira do usuário (senão 404).
        Pós: carteira e associações removidas; operações de compra/venda mantidas."""
        ...

    def associate_investment(
        self, user_id: int, portfolio_id: int, stock_id: int
    ) -> models.Portfolio:
        """associarInvestimento. Pré: carteira do usuário (senão 404) e stock_id
        existente (garantido pelo Investment Component).
        Pós: o ativo fica em exatamente uma carteira (associar de novo move)."""
        ...

    def dissociate_investment(self, user_id: int, stock_id: int) -> bool:
        """Desfaz a associação do ativo. Pós: retorna True se havia associação."""
        ...

    def get_investment_portfolios(self, user_id: int) -> dict[int, models.Portfolio]:
        """Mapa stock_id -> carteira usado para montar as posições do usuário."""
        ...


class IInvestmentService(Protocol):
    """
    Interface fornecida pelo Investment Component (Lab 3: IInvestmentService).

    Interfaces requeridas: IPortfolioService (carteiras) e IMarketDataService
    (validação do ticker e cotação).
    """

    async def create_trade(
        self, user_id: int, trade_in: StockTradeCreate
    ) -> models.UserStock:
        """registrarMovimentacao / cadastrarAcao. Pré: ticker ativo na B3,
        corretora cadastrada, saldo suficiente em vendas (senão 422) e, se
        informada, carteira do usuário (senão 404).
        Pós: operação persistida e, com portfolio_id, ativo associado à carteira."""
        ...

    def list_trades(self, user_id: int) -> list[models.UserStock]:
        """consultarInvestimentos (histórico). Pós: operações do usuário, mais recentes primeiro."""
        ...

    def get_positions(
        self, user_id: int, portfolio_id: int | None = None
    ) -> list[PositionOut]:
        """consultarInvestimentos (consolidado). Pré: se portfolio_id for
        informado, a carteira é do usuário (senão 404).
        Pós: posições com quantidade > 0, preço médio e carteira associada."""
        ...

    def associate_position(
        self, user_id: int, stock_name: str, portfolio_id: int
    ) -> PositionOut:
        """editarInvestimento (associar ação à carteira). Pré: usuário possui
        posição aberta no ativo (senão 404) e a carteira é dele (senão 404).
        Pós: posição devolvida já com a nova carteira."""
        ...

    def remove_position(self, user_id: int, stock_name: str) -> int:
        """removerInvestimento. Pré: ativo existe na carteira do usuário (senão 404).
        Pós: operações e associação à carteira removidas; retorna o total apagado."""
        ...
