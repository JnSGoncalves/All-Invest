"""
Fixtures compartilhadas pelos testes dos componentes Portfolio e Investment.

Os testes usam SQLite em memória e um stub do Market Data. Nada acessa o
Supabase nem a brapi.dev, então rodam offline e sem o backend/.env.
"""

import os
from decimal import Decimal

# Precisa vir antes de importar `src`: database.py e security.py leem o
# ambiente no import, e load_dotenv não sobrescreve variáveis já definidas.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "chave-somente-para-testes"
os.environ["BRAPI_TOKEN"] = "token-de-teste"

import pytest
from fastapi import HTTPException, status
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import models
from src.db.database import Base
from src.services.investment_service import InvestmentService
from src.services.portfolio_service import PortfolioService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SAVEPOINT (begin_nested) e FKs funcionando no driver sqlite3.
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _record):
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def _on_begin(connection):
        connection.exec_driver_sql("BEGIN")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    yield session
    session.close()


def _create_user(db, name: str, email: str) -> models.User:
    user = models.User(name=name, email=email, password_hash="hash-irrelevante")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user(db):
    return _create_user(db, "Investidora Teste", "investidora@example.com")


@pytest.fixture
def other_user(db):
    return _create_user(db, "Outra Pessoa", "outra@example.com")


class FakeMarketDataService:
    """Stub de IMarketDataService: tickers conhecidos e cotação fixa."""

    TICKERS = {
        "PETR4": "Petróleo Brasileiro S.A. - Petrobras",
        "VALE3": "Vale S.A.",
        "ITUB4": "Itaú Unibanco Holding S.A.",
    }

    def __init__(self, quote: Decimal = Decimal("38.50")) -> None:
        self.quote = quote
        self.calls: list[tuple[str, str]] = []

    async def validate_ticker(self, stock_name: str) -> dict:
        ticker = stock_name.strip().upper()
        self.calls.append(("validate_ticker", ticker))
        if ticker not in self.TICKERS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"O ativo '{ticker}' não foi encontrado na B3.",
            )
        return {"stock_name": ticker, "company_name": self.TICKERS[ticker]}

    async def get_quote(self, stock_name: str) -> Decimal:
        self.calls.append(("get_quote", stock_name))
        return self.quote

    async def list_tickers(self, search=None, tipo=None, page=1, limit=20) -> dict:
        return {"results": [], "page": 1, "total_pages": 1, "total_items": 0, "has_next_page": False}

    async def autocomplete_tickers(self, query: str, limit: int = 8) -> list[dict]:
        return []


@pytest.fixture
def market_data():
    return FakeMarketDataService()


@pytest.fixture
def portfolio_service(db):
    return PortfolioService(db)


@pytest.fixture
def investment_service(db, market_data, portfolio_service):
    """Investment real integrado ao Portfolio real pela interface IPortfolioService."""
    return InvestmentService(db, market_data, portfolio_service)
