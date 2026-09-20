from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from .db.crud import validate_api_key
from .db.database import SessionLocal
from .routers import users
from .routers import auth
import os
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
load_dotenv()

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
    public_prefixes = ("/api/v1/auth",)
    request_path = request.url.path.rstrip("/") or "/"

    # O preflight CORS não envia X-API-Key. Todas as rotas de autenticação
    # também precisam ser públicas para que o usuário consiga entrar.
    if (
        request.method == "OPTIONS"
        or request_path in public_routes
        or any(
            request_path == prefix or request_path.startswith(f"{prefix}/")
            for prefix in public_prefixes
        )
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

    public_auth_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/google",
        "/api/v1/auth/google/callback",
    }

    for public_path, path_item in openapi_schema.get("paths", {}).items():
        for operation in path_item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            if public_path == "/health" or public_path in public_auth_paths:
                operation["security"] = []
            elif not public_path.startswith("/api/v1/auth"):
                requirements = operation.get("security", [])
                if any("BearerAuth" in requirement for requirement in requirements):
                    operation["security"] = [
                        {"ApiKeyAuth": [], "BearerAuth": []}
                    ]

    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi
