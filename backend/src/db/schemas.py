from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

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
    """Payload de cadastro de uma operação de compra/venda."""
 
    stock_name: str = Field(..., min_length=4, max_length=10, examples=["PETR4"])
    stock_quantity: int = Field(..., gt=0, examples=[100])
    stock_price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=15,
        decimal_places=4,
        description=(
            "Preço pago na operação. Obrigatório quando auto_cotacao=False. "
            "Deve ser omitido quando auto_cotacao=True."
        ),
    )
    auto_cotacao: bool = Field(
        default=False,
        description=(
            "Se true, a API ignora stock_price e busca automaticamente a "
            "cotação atual do ativo na B3 no momento do cadastro. "
            "Se false (padrão), stock_price é obrigatório."
        ),
    )
    broker_id: int = Field(..., gt=0)
    trade_side: Literal["BUY", "SELL"]
    trade_date: Optional[datetime] = None
 
    @field_validator("stock_name")
    @classmethod
    def normalizar_ticker(cls, v: str) -> str:
        return v.strip().upper()
 
    @field_validator("trade_date")
    @classmethod
    def nao_permitir_data_futura(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v > datetime.now(v.tzinfo):
            raise ValueError("A data da operação não pode ser futura.")
        return v
 
    @model_validator(mode="after")
    def validar_combinacao_preco(self) -> "StockTradeCreate":
        if self.auto_cotacao and self.stock_price is not None:
            raise ValueError(
                "stock_price não deve ser informado quando auto_cotacao=true. "
                "Envie apenas um dos dois."
            )
        if not self.auto_cotacao and self.stock_price is None:
            raise ValueError(
                "stock_price é obrigatório quando auto_cotacao=false. "
                "Informe o preço ou defina auto_cotacao=true."
            )
        return self

class StockTradeOut(BaseModel):
    """Retorno de uma operação registrada."""

    model_config = ConfigDict(from_attributes=True)

    stock_name: str
    company_name: str
    stock_quantity: int
    stock_price: Decimal
    broker_id: int
    broker_name: str
    trade_side: str
    trade_date: datetime

class PositionOut(BaseModel):
    """Posição consolidada de um ativo na carteira."""

    model_config = ConfigDict(from_attributes=True)

    stock_name: str
    company_name: str
    stock_quantity: int
    preco_medio: Decimal

class StockValidationOut(BaseModel):
    """Resultado da validação de um ticker na B3."""

    stock_name: str
    company_name: str
    valido: bool
    
class TickerOut(BaseModel):
    """Ticker normalizado retornado pela brapi.dev."""
 
    stock_name: str
    company_name: str
    asset_type: Optional[str] = None
    sector: Optional[str] = None
    is_active: bool = True
    logo_url: Optional[str] = None
 
 
class TickerListOut(BaseModel):
    """Resposta paginada de listagem de tickers."""
 
    results: list[TickerOut]
    page: int
    total_pages: int
    total_items: int
    has_next_page: bool
 
 
class TickerAutocompleteOut(BaseModel):
    """Item leve para sugestões de autocomplete no front."""
 
    stock_name: str
    company_name: str
      
# Compatibilidade temporária para imports antigos.
Token = TokenPair