from fastapi import FastAPI

from .database import Base, engine
from .routers import users

# Cria as tabelas no banco a partir dos models
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="All Invest API",
    description="API do HUB unificado de investimentos All Invest.",
    version="0.1.0",
)

app.include_router(users.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
