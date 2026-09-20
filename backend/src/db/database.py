import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não configurada. Use a connection string PostgreSQL do Supabase no arquivo .env."
    )

# A conexão direta do Supabase usa IPv6. Em redes locais IPv4, esta opção
# troca apenas host/usuário pelo Session pooler e preserva a senha existente.
pooler_host = os.getenv("DATABASE_POOLER_HOST")
if pooler_host:
    database_url = make_url(DATABASE_URL)
    direct_host = database_url.host or ""
    if direct_host.startswith("db.") and direct_host.endswith(".supabase.co"):
        project_ref = direct_host.removeprefix("db.").removesuffix(".supabase.co")
        database_url = database_url.set(
            host=pooler_host,
            port=5432,
            username=f"{database_url.username}.{project_ref}",
        )
        DATABASE_URL = database_url.render_as_string(hide_password=False)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre uma sessão por request e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
