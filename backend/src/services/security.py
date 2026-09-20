import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "chave-de-desenvolvimento-troque-em-producao")
ALGORITHM = "HS256"
TOKEN_ISSUER = "all-invest"
TOKEN_AUDIENCE = "all-invest-api"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

if (
    os.getenv("ENVIRONMENT", "development").lower() == "production"
    and SECRET_KEY == "chave-de-desenvolvimento-troque-em-producao"
):
    raise RuntimeError("SECRET_KEY deve ser configurada em produção.")


class InvalidAccessTokenError(Exception):
    """O access token não é válido para esta API."""


class ExpiredAccessTokenError(InvalidAccessTokenError):
    """O access token era válido, mas expirou."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def create_access_token(user_id: int) -> str:
    issued_at = utc_now()
    expires_at = issued_at + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": expires_at,
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
            options={"require": ["sub", "type", "jti", "iat", "exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredAccessTokenError from exc
    except (jwt.PyJWTError, TypeError) as exc:
        raise InvalidAccessTokenError from exc

    if payload.get("type") != "access":
        raise InvalidAccessTokenError

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise InvalidAccessTokenError from exc

    if user_id <= 0:
        raise InvalidAccessTokenError
    return user_id


def generate_refresh_token() -> str:
    """Gera o segredo entregue ao cliente; somente o hash vai para o banco."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def refresh_token_expiration() -> datetime:
    return utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


def access_token_expires_in_seconds() -> int:
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60
