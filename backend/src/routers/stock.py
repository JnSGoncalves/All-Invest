from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import schemas
from ..db.database import get_db
from ..services.auth_services import get_current_user  # placeholder OAuth 2.0

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


# ===========================================================================
# MOCKS TEMPORÁRIOS
# ---------------------------------------------------------------------------
# Serão substituídos por:
#   - B3_TICKERS  -> consulta real à API da B3 (ou tabela `stocks` populada)
#   - _MOCK_WALLET -> persistência real na tabela `users_stocks` via crud.py
# ===========================================================================
B3_TICKERS = {
    "PETR4": "Petróleo Brasileiro S.A. - Petrobras",
    "VALE3": "Vale S.A.",
    "ITUB4": "Itaú Unibanco Holding S.A.",
    "BBDC4": "Banco Bradesco S.A.",
    "ABEV3": "Ambev S.A.",
    "BBAS3": "Banco do Brasil S.A.",
    "MGLU3": "Magazine Luiza S.A.",
    "WEGE3": "WEG S.A.",
    "B3SA3": "B3 S.A. - Brasil, Bolsa, Balcão",
    "RENT3": "Localiza Rent a Car S.A.",
}

# Corretoras aceitas enquanto a tabela `brokers` não está populada
MOCK_BROKERS = {1: "XP Investimentos", 2: "Rico", 3: "Clear", 4: "NuInvest"}

# Carteira em memória: { user_id: [ {..operação..} ] }
_MOCK_WALLET: dict[int, List[dict]] = {}


def validar_ticker_b3(stock_name: str) -> str:
    """
    Mock da validação de existência da ação na B3.

    Retorna o nome da empresa se o ticker existir.
    TODO: trocar por chamada à API da B3 / brapi / consulta na tabela `stocks`.
    """
    ticker = stock_name.strip().upper()
    if ticker not in B3_TICKERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O ativo '{ticker}' não foi encontrado na B3.",
        )
    return B3_TICKERS[ticker]


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
def cadastrar_operacao(
    trade_in: schemas.StockTradeCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
):
    """
    Cadastro de operação de compra/venda de ações na carteira do usuário.

    CA01: ticker válido na B3 + dados corretos -> registra e retorna 201.
    CA02: ticker inexistente na B3 -> 404 com mensagem clara.
    CA03: venda maior que a posição atual -> 422 (saldo insuficiente).
    CA04: corretora não cadastrada -> 400.
    """
    ticker = trade_in.stock_name.strip().upper()
    company_name = validar_ticker_b3(ticker)

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
        "stock_price": trade_in.stock_price,
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
def validar_ativo(stock_name: str):
    """Verifica se um ticker existe na B3 (mock). Útil para validação no front."""
    ticker = stock_name.strip().upper()
    company_name = validar_ticker_b3(ticker)
    return {"stock_name": ticker, "company_name": company_name, "valido": True}