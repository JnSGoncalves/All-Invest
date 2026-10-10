import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

# Carrega a configuração antes de importar módulos que constroem o engine SQLAlchemy.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .db.crud import validate_api_key
from .db.database import SessionLocal
from .routers import users
from .routers import auth
from .routers import stocks
from .routers import portfolios
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title="All Invest API",
    description="""
API do HUB unificado de investimentos All Invest.

### Testar login com Google

O OAuth não pode ser iniciado pelo botão **Execute** do Swagger, pois ele usa
`fetch` e o redirecionamento externo do Google é bloqueado pelo navegador.

<a href="/api/v1/auth/google" target="_blank"><strong>▶ Abrir login com Google em uma nova aba</strong></a>

Depois do login, o callback exibirá o `access_token` e o `refresh_token`.
""",
    version="0.1.0",
)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    public_routes = {
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
    }
    request_path = request.url.path.rstrip("/") or "/"
    oauth_routes_without_api_key = {
        "/api/v1/auth/google",
        "/api/v1/auth/google/callback",
    }

    # O preflight CORS não envia X-API-Key. O início e o callback OAuth do
    # Google são exceções porque o navegador/provedor não enviam esse header
    # durante os redirecionamentos; os demais endpoints de auth exigem a chave.
    if (
        request.method == "OPTIONS"
        or request_path in public_routes
        or request_path in oauth_routes_without_api_key
    ):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "API Key não informada"},
        )

    db = SessionLocal()

    try:
        if not validate_api_key(db, api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "API Key inválida"},
            )

        return await call_next(request)

    finally:
        db.close()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET_KEY",
        os.getenv("SECRET_KEY", "chave-de-desenvolvimento-troque-em-producao"),
    ),
    session_cookie="allinvest_oauth_session",
    max_age=600,
    same_site="lax",
    https_only=os.getenv("ENVIRONMENT", "development").lower() == "production",
)

        
default_cors_origins = [
    "http://localhost:5173",
    "http://localhost:4671",
]
cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", ",".join(default_cors_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)


app.include_router(users.router)
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(portfolios.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    security_schemes = openapi_schema.setdefault("components", {}).setdefault(
        "securitySchemes", {}
    )
    security_schemes["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }

    openapi_schema["security"] = [
        {"ApiKeyAuth": []}
    ]

    oauth_paths = {
        "/api/v1/auth/google",
        "/api/v1/auth/google/callback",
    }

    for public_path, path_item in openapi_schema.get("paths", {}).items():
        for operation in path_item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            if public_path == "/health" or public_path in oauth_paths:
                operation["security"] = []
            elif public_path.startswith("/api/v1/auth"):
                requirements = operation.get("security", [])
                if any("BearerAuth" in requirement for requirement in requirements):
                    operation["security"] = [
                        {"ApiKeyAuth": [], "BearerAuth": []}
                    ]
                else:
                    operation["security"] = [{"ApiKeyAuth": []}]
            elif not public_path.startswith("/api/v1/auth"):
                requirements = operation.get("security", [])
                if any("BearerAuth" in requirement for requirement in requirements):
                    operation["security"] = [
                        {"ApiKeyAuth": [], "BearerAuth": []}
                    ]

    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi
