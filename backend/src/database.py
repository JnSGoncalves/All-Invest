import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Ex.: postgresql://usuario:senha@localhost:5432/all_invest
# Troque para a string de conexão do banco (Postgres, MySQL, etc.)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./all_invest.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre uma sessão por request e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
