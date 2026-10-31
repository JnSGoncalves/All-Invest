"""Servidor HTTP isolado para Playwright; só o provedor de mercado é simulado.

Executar na pasta backend: python -m tests.e2e_server.
Usa banco temporário e chave de teste, sem acessar o banco configurado no .env.
"""

import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "e2e-local-secret-key-at-least-32-bytes"
os.environ["SESSION_SECRET_KEY"] = "e2e-local-session-key-at-least-32-bytes"

import uvicorn
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from tests.conftest import FakeMarketDataService
from src import main, models
from src.db.database import Base, get_db
from src.dependencies.components import get_market_data_service


def run():
    with tempfile.TemporaryDirectory(prefix="allinvest-e2e-") as folder:
        engine = create_engine("sqlite:///" + (Path(folder) / "test.db").as_posix(),
                               connect_args={"check_same_thread": False})
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)
        with sessions() as db:
            db.add(models.ApiKey(project_name="Playwright", api_key="e2e-local-api-key"))
            db.commit()
        def test_db():
            with sessions() as db:
                yield db
        main.SessionLocal = sessions
        main.app.dependency_overrides[get_db] = test_db
        main.app.dependency_overrides[get_market_data_service] = FakeMarketDataService
        try:
            uvicorn.run(main.app, host="127.0.0.1", port=8175, log_level="warning")
        finally:
            engine.dispose()


if __name__ == "__main__":
    run()
