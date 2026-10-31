"""
services/market_data_service.py

Integração com a brapi.dev para:
  - validar se um ticker existe e está ativo na B3 antes do cadastro
  - listar os tickers disponíveis (screener simples)
  - fornecer sugestões de autocomplete para o front

Endpoint utilizado: GET {BRAPI_URL}/tickers
Docs: https://brapi.dev/docs/tickers
"""

import os
from collections import OrderedDict
from datetime import date, datetime, timezone
from decimal import Decimal
from time import monotonic
from typing import Optional

import httpx
from fastapi import HTTPException, status
from ..db.schemas import HistoricalPrice

BRAPI_URL = os.getenv("BRAPI_URL", "https://brapi.dev/api/v2")
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN")
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_HISTORY_CACHE: OrderedDict[tuple, tuple[float, tuple[HistoricalPrice, ...]]] = OrderedDict()
_HISTORY_TTL = 900
_HISTORY_CACHE_SIZE = 256


async def _get(path: str, params: dict) -> dict:
    """Wrapper de requisição GET com tratamento de erros de rede/HTTP."""
    if not BRAPI_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BRAPI_TOKEN não configurado no servidor.",
        )

    url = f"{BRAPI_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {BRAPI_TOKEN}"},
                params=params,
            )
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

    if response.status_code >= 400:
        raise HTTPException(502, "Recurso indisponível na brapi.dev. Verifique a cobertura e o plano contratado.")
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Formato inválido")
        return data
    except ValueError as exc:
        raise HTTPException(502, "Resposta inválida da brapi.dev.") from exc


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
            detail="Tente novamente! Esse ativo não existe na B3.",
        )

    if not correspondencia.get("isActive", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O ativo '{ticker}' está inativo/deslistado na B3.",
        )

    return _map_resultado(correspondencia)


async def obter_cotacao(stock_name: str) -> Decimal:
    """
    Busca a cotação atual (preço de mercado) de um ticker.

    Usado quando `stock_price` não é informado no cadastro da operação
    (POST /api/stocks) — a API preenche automaticamente com o preço
    corrente da B3 no momento do cadastro.

    Usa /stocks/quote em vez de /tickers porque é o endpoint dedicado
    a cotação (mais atualizado; /tickers pode trazer preço em cache
    de listagem/screener).
    """
    ticker = stock_name.strip().upper()
    data = await _get("/stocks/quote", {"symbols": ticker})

    resultados = data.get("results", [])
    if not resultados or "data" not in resultados[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cotação não encontrada para '{ticker}'.",
        )

    preco = resultados[0]["data"].get("regularMarketPrice")
    if preco is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cotação indisponível no momento para '{ticker}'.",
        )

    return Decimal(str(preco))


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


class BrapiMarketDataService:
    """Implementação brapi.dev do contrato do componente Market Data."""

    async def validate_ticker(self, stock_name: str) -> dict:
        return await validar_ticker(stock_name)

    async def get_quote(self, stock_name: str) -> Decimal:
        return await obter_cotacao(stock_name)

    async def get_history(self, stock_name: str, start: date, end: date) -> list[HistoricalPrice]:
        ticker = stock_name.strip().upper()
        key = (BRAPI_URL, ticker, start, end)
        cached = _HISTORY_CACHE.get(key)
        if cached and cached[0] > monotonic():
            _HISTORY_CACHE.move_to_end(key)
            return [point.model_copy() for point in cached[1]]
        # Quantidades reais exigem preços sem ajuste: close pode incluir proventos.
        data = await _get("/stocks/historical", {
            "symbols": ticker, "startDate": start.isoformat(), "endDate": end.isoformat(),
            "interval": "1d", "sortOrder": "asc", "includeRaw": "true",
        })
        try:
            result = next(item for item in data["results"]
                          if item.get("requestedSymbol", item.get("symbol", "")).upper() == ticker)
            points = {}
            for item in result["data"]["historicalDataPrice"]:
                day = datetime.fromtimestamp(item["date"], timezone.utc).date()
                if start <= day <= end:
                    points[day] = HistoricalPrice(date=day, close=item["rawClose"])
            history = sorted(points.values(), key=lambda point: point.date)
            if not history:
                raise ValueError("Histórico vazio")
        except (AttributeError, KeyError, TypeError, ValueError, StopIteration, OverflowError, OSError) as exc:
            raise HTTPException(502, f"Histórico sem preços originais válidos para {ticker}.") from exc
        _HISTORY_CACHE[key] = (monotonic() + _HISTORY_TTL, tuple(history))
        _HISTORY_CACHE.move_to_end(key)
        while len(_HISTORY_CACHE) > _HISTORY_CACHE_SIZE:
            _HISTORY_CACHE.popitem(last=False)
        return [point.model_copy() for point in history]

    async def list_tickers(
        self,
        search: Optional[str] = None,
        tipo: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        return await listar_tickers(search=search, tipo=tipo, page=page, limit=limit)

    async def autocomplete_tickers(
        self, query: str, limit: int = 8
    ) -> list[dict]:
        return await autocomplete_tickers(query, limit=limit)
