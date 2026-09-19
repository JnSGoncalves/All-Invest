"""
services/ticker_services.py

Integração com a brapi.dev para:
  - validar se um ticker existe e está ativo na B3 antes do cadastro
  - listar os tickers disponíveis na B3 com paginação e filtro
  - fornecer sugestões de autocomplete para o front

Endpoint utilizado: GET {BRAPI_URL}/tickers
Docs: https://brapi.dev/docs/tickers
"""

import os
from typing import Optional

import httpx
from fastapi import HTTPException, status

BRAPI_URL = os.getenv("BRAPI_URL", "https://brapi.dev/api/v2")
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN")

if not BRAPI_TOKEN:
    raise RuntimeError(
        "BRAPI_TOKEN não configurado. Defina a variável no arquivo .env."
    )

_HEADERS = {"Authorization": f"Bearer {BRAPI_TOKEN}"}
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def _get(path: str, params: dict) -> dict:
    """Wrapper de requisição GET com tratamento de erros de rede/HTTP."""
    url = f"{BRAPI_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=_HEADERS, params=params)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo de resposta da brapi.dev excedido. Tente novamente.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar à brapi.dev.",
        )

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Token da brapi.dev inválido ou expirado.",
        )
    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de requisições à brapi.dev atingido. Tente novamente em instantes.",
        )
    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro no serviço da brapi.dev.",
        )

    response.raise_for_status()
    return response.json()


def _map_resultado(item: dict) -> dict:
    """Normaliza um item de `results[]` da brapi para o formato interno."""
    return {
        "stock_name": item["symbol"],
        "company_name": item.get("longName") or item.get("name", ""),
        "asset_type": item.get("assetType"),
        "sector": item.get("sector"),
        "is_active": item.get("isActive", True),
        "logo_url": item.get("logoUrl"),
    }


async def validar_ticker(stock_name: str) -> dict:
    """
    Valida se um ticker existe e está ativo na B3.

    Usado antes do cadastro de uma operação (POST /api/stocks).
    Levanta 404 se o ticker não existir ou estiver inativo.
    """
    ticker = stock_name.strip().upper()
    data = await _get("/tickers", {"search": ticker, "limit": 10})

    resultados = data.get("results", [])
    correspondencia = next(
        (item for item in resultados if item["symbol"].upper() == ticker),
        None,
    )

    if correspondencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O ativo '{ticker}' não foi encontrado na B3.",
        )

    if not correspondencia.get("isActive", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O ativo '{ticker}' está inativo/deslistado na B3.",
        )

    return _map_resultado(correspondencia)


async def listar_tickers(
    search: Optional[str] = None,
    tipo: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """
    Lista os tickers cadastrados na B3, com paginação e filtro opcional.

    `tipo`: "stock", "fund" ou "bdr" (mesmo domínio aceito pela brapi).
    """
    params = {"page": page, "limit": min(limit, 100)}
    if search:
        params["search"] = search.strip().upper()
    if tipo:
        params["type"] = tipo

    data = await _get("/tickers", params)

    return {
        "results": [_map_resultado(item) for item in data.get("results", [])],
        "page": data.get("pagination", {}).get("page", page),
        "total_pages": data.get("pagination", {}).get("totalPages", 1),
        "total_items": data.get("pagination", {}).get("totalItems", 0),
        "has_next_page": data.get("pagination", {}).get("hasNextPage", False),
    }


async def autocomplete_tickers(query: str, limit: int = 8) -> list[dict]:
    """
    Retorna sugestões leves de tickers para autocomplete no front.

    Formato enxuto (sem setor/logo) pensado para resposta rápida
    enquanto o usuário digita.
    """
    query = query.strip()
    if len(query) < 1:
        return []

    data = await _get(
        "/tickers",
        {"search": query.upper(), "limit": limit, "sortBy": "volume", "sortOrder": "desc"},
    )

    return [
        {
            "stock_name": item["symbol"],
            "company_name": item.get("longName") or item.get("name", ""),
        }
        for item in data.get("results", [])
        if item.get("isActive", True)
    ]
