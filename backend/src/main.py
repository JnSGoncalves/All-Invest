from fastapi import FastAPI

from .routers import users
from .routers import auth

app = FastAPI(
    title="All Invest API",
    description="API do HUB unificado de investimentos All Invest.",
    version="0.1.0",
)

app.include_router(users.router)
app.include_router(auth.router)



@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
