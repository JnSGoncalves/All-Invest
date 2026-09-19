from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import schemas
from ..db.database import get_db
from ..services import ticker_services
from ..services.auth_services import get_current_user  # placeholder OAuth 2.0

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


# ===========================================================================
# MOCKS TEMPORÁRIOS
# ---------------------------------------------------------------------------
# A validação de ticker agora é real, via ticker_services (brapi.dev).
# Ainda restam mockados:
#   - MOCK_BROKERS -> consulta real à tabela `brokers`
#   - _MOCK_WALLET  -> persistência real na tabela `users_stocks` via crud.py
# ===========================================================================

# Corretoras aceitas enquanto a tabela `brokers` não está populada
MOCK_BROKERS = {1: "XP Investimentos", 2: "Rico", 3: "Clear", 4: "NuInvest"}

# Carteira em memória: { user_id: [ {..operação..} ] }
_MOCK_WALLET: dict[int, List[dict]] = {}


def _saldo_em_carteira(user_id: int, ticker: str) -> int:
    """Calcula a quantidade líquida (compras - vendas) de um ativo na carteira mock."""
    operacoes = _MOCK_WALLET.get(user_id, [])
    return sum(
        op["stock_quantity"] if op["trade_side"] == "BUY" else -op["stock_quantity"]
        for op in operacoes
        if op["stock_name"] == ticker
    )


# ===========================================================================
# ENDPOINTS
# ===========================================================================


@router.post(
    "",
    response_model=schemas.StockTradeOut,
    status_code=status.HTTP_201_CREATED,
)
async def cadastrar_operacao(
    trade_in: schemas.StockTradeCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
):
    """
    Cadastro de operação de compra/venda de ações na carteira do usuário.

    CA01: ticker válido na B3 (brapi.dev) + dados corretos -> registra e retorna 201.
    CA02: ticker inexistente/inativo na B3 -> 404 com mensagem clara.
    CA03: venda maior que a posição atual -> 422 (saldo insuficiente).
    CA04: corretora não cadastrada -> 400.
    """
    ticker_info = await ticker_services.validar_ticker(trade_in.stock_name)
    ticker = ticker_info["stock_name"]
    company_name = ticker_info["company_name"]

    # stock_price manual (auto_cotacao=False) ou buscado na B3 (auto_cotacao=True).
    # A consistência entre os dois campos já foi validada no schema.
    stock_price = trade_in.stock_price
    if trade_in.auto_cotacao:
        stock_price = await ticker_services.obter_cotacao(ticker)

    if trade_in.broker_id not in MOCK_BROKERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corretora não cadastrada para este usuário.",
        )

    if trade_in.trade_side == "SELL":
        saldo_atual = _saldo_em_carteira(current_user.user_id, ticker)
        if trade_in.stock_quantity > saldo_atual:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Saldo insuficiente para venda. Posição atual de {ticker}: "
                    f"{saldo_atual} ação(ões)."
                ),
            )

    operacao = {
        "user_id": current_user.user_id,
        "stock_name": ticker,
        "company_name": company_name,
        "stock_quantity": trade_in.stock_quantity,
        "stock_price": stock_price,
        "broker_id": trade_in.broker_id,
        "broker_name": MOCK_BROKERS[trade_in.broker_id],
        "trade_side": trade_in.trade_side,
        "trade_date": trade_in.trade_date or datetime.now(timezone.utc),
    }

    # TODO: substituir pelo insert real:
    #   return crud.create_user_stock(db, current_user.user_id, trade_in)
    _MOCK_WALLET.setdefault(current_user.user_id, []).append(operacao)

    return operacao


@router.get("", response_model=List[schemas.StockTradeOut])
def listar_operacoes(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
):
    """Lista todas as operações registradas na carteira do usuário autenticado."""
    # TODO: substituir por crud.get_user_stocks(db, current_user.user_id)
    return _MOCK_WALLET.get(current_user.user_id, [])


@router.get("/carteira", response_model=List[schemas.PositionOut])
def consultar_carteira(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
):
    """Retorna a posição consolidada (quantidade líquida e preço médio) por ativo."""
    operacoes = _MOCK_WALLET.get(current_user.user_id, [])
    posicoes: dict[str, dict] = {}

    for op in operacoes:
        pos = posicoes.setdefault(
            op["stock_name"],
            {
                "stock_name": op["stock_name"],
                "company_name": op["company_name"],
                "stock_quantity": 0,
                "custo_total": Decimal("0"),
            },
        )
        if op["trade_side"] == "BUY":
            pos["stock_quantity"] += op["stock_quantity"]
            pos["custo_total"] += Decimal(str(op["stock_price"])) * op["stock_quantity"]
        else:
            pos["stock_quantity"] -= op["stock_quantity"]
            pos["custo_total"] -= Decimal(str(op["stock_price"])) * op["stock_quantity"]

    return [
        {
            "stock_name": p["stock_name"],
            "company_name": p["company_name"],
            "stock_quantity": p["stock_quantity"],
            "preco_medio": (
                (p["custo_total"] / p["stock_quantity"]).quantize(Decimal("0.0001"))
                if p["stock_quantity"] > 0
                else Decimal("0")
            ),
        }
        for p in posicoes.values()
        if p["stock_quantity"] != 0
    ]


@router.get("/validar/{stock_name}", response_model=schemas.StockValidationOut)
async def validar_ativo(stock_name: str):
    """Verifica se um ticker existe e está ativo na B3 (via brapi.dev). Útil para validação no front."""
    ticker_info = await ticker_services.validar_ticker(stock_name)
    return {
        "stock_name": ticker_info["stock_name"],
        "company_name": ticker_info["company_name"],
        "valido": True,
    }


@router.get("/buscar", response_model=schemas.TickerListOut)
async def buscar_tickers(
    search: str | None = None,
    tipo: str | None = None,
    page: int = 1,
    limit: int = 20,
):
    """
    Lista/filtra os tickers disponíveis na B3 (screener paginado via brapi.dev).

    Query params opcionais: `search` (texto livre), `tipo` (stock/fund/bdr),
    `page` e `limit`.
    """
    return await ticker_services.listar_tickers(
        search=search, tipo=tipo, page=page, limit=limit
    )


@router.get("/autocomplete", response_model=List[schemas.TickerAutocompleteOut])
async def autocomplete_tickers(q: str, limit: int = 8):
    """
    Sugestões de tickers para autocomplete no front, conforme o usuário digita.

    Exemplo: GET /api/stocks/autocomplete?q=PETR -> [{PETR3, PETR4, ...}]
    """
    return await ticker_services.autocomplete_tickers(q, limit=limit)