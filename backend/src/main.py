from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from .db.crud import validate_api_key
from .db.database import SessionLocal
from .routers import stocks, users, auth


app = FastAPI(
    title="All Invest API",
    description="API do HUB unificado de investimentos All Invest.",
    version="0.1.0",
)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    public_routes = [
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
    ]

    if request.url.path in public_routes:
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
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Frontend pelo Vite
        "http://localhost:4671",  # Frontend pelo Docker
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)


app.include_router(users.router)
app.include_router(auth.router)
app.include_router(stocks.router)


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

    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }

    # Enquanto o OAuth2 ainda é placeholder (auth_services.get_current_user
    # sempre retorna um usuário mock), removemos o esquema OAuth2 gerado
    # automaticamente pelo FastAPI e deixamos só a ApiKeyAuth exigida.
    # TODO: remover este bloco quando o OAuth2 for implementado de verdade.
    OAUTH_PLACEHOLDER_ATIVO = True

    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            security = operation.get("security", [])
            if OAUTH_PLACEHOLDER_ATIVO:
                security = [
                    req for req in security if "OAuth2PasswordBearer" not in req
                ]
            if not any("ApiKeyAuth" in req for req in security):
                security.append({"ApiKeyAuth": []})
            operation["security"] = security

    if OAUTH_PLACEHOLDER_ATIVO:
        openapi_schema["components"]["securitySchemes"].pop(
            "OAuth2PasswordBearer", None
        )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi