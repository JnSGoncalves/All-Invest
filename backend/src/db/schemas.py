from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 bytes.")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: EmailStr
    created_at: datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Validade do access token, em segundos")


class AuthResponse(TokenPair):
    user: UserOut


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class LogoutRequest(RefreshTokenRequest):
    pass


class MessageResponse(BaseModel):
    message: str


class StockTradeCreate(BaseModel):
    stock_name: str = Field(min_length=1, max_length=20)
    stock_quantity: int = Field(gt=0)
    stock_price: Decimal | None = Field(default=None, gt=0, max_digits=15, decimal_places=4)
    broker_id: int = Field(gt=0)
    trade_side: Literal["BUY", "SELL"]
    trade_date: datetime | None = None
    auto_cotacao: bool = False
    portfolio_id: int | None = Field(
        default=None,
        gt=0,
        description="Carteira (Portfolio Component) à qual o ativo será associado.",
    )

    @field_validator("stock_name")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("O ticker não pode ser vazio.")
        return ticker

    @field_validator("trade_date")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("trade_date deve incluir fuso horário.")
        return value

    def model_post_init(self, __context: object) -> None:
        if self.auto_cotacao and self.stock_price is not None:
            raise ValueError("Não informe stock_price quando auto_cotacao for true.")
        if not self.auto_cotacao and self.stock_price is None:
            raise ValueError("Informe stock_price ou defina auto_cotacao como true.")


class StockTradeOut(BaseModel):
    stock_name: str
    company_name: str
    stock_quantity: int
    stock_price: Decimal
    broker_id: int
    broker_name: str
    trade_side: Literal["BUY", "SELL"]
    trade_date: datetime


class PositionOut(BaseModel):
    stock_name: str
    company_name: str
    stock_quantity: int
    preco_medio: Decimal
    portfolio_id: int | None = None
    portfolio_name: str | None = None


class PortfolioCreate(BaseModel):
    portfolio_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("portfolio_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("O nome da carteira não pode ser vazio.")
        return name


class PortfolioUpdate(BaseModel):
    portfolio_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("portfolio_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("O nome da carteira não pode ser nulo.")
        name = value.strip()
        if not name:
            raise ValueError("O nome da carteira não pode ser vazio.")
        return name

    @model_validator(mode="after")
    def require_changes(self) -> "PortfolioUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para alterar.")
        return self


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    portfolio_id: int
    portfolio_name: str
    description: str | None = None
    created_at: datetime


class PortfolioAssignment(BaseModel):
    portfolio_id: int = Field(gt=0)


class StockValidationOut(BaseModel):
    stock_name: str
    company_name: str
    valido: bool


class TickerAutocompleteOut(BaseModel):
    stock_name: str
    company_name: str


class TickerOut(TickerAutocompleteOut):
    asset_type: str | None = None
    sector: str | None = None
    is_active: bool
    logo_url: str | None = None


class TickerListOut(BaseModel):
    results: list[TickerOut]
    page: int
    total_pages: int
    total_items: int
    has_next_page: bool


# Compatibilidade temporária para imports antigos.
Token = TokenPair
