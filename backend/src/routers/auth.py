import os
import logging
from urllib.parse import urlencode, urlsplit
from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..dependencies.auth import CurrentUser
from ..services import security, tokens
from ..db import crud
from ..db import schemas
from ..db.database import get_db
from ..services.google.auth import google_is_configured, oauth

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _oauth_error_detail(exc: OAuthError) -> str:
    """Traduz erros OAuth sem devolver tokens ou outros dados sensíveis."""
    error_code = getattr(exc, "error", None) or "oauth_error"
    messages = {
        "mismatching_state": (
            "A sessão de login expirou ou foi iniciada em outro endereço. "
            "Abra o login pelo Swagger novamente."
        ),
        "invalid_client": (
            "O Client ID ou Client Secret configurado no backend é inválido."
        ),
        "invalid_grant": (
            "O código do Google expirou, já foi utilizado ou foi emitido para "
            "outra URI de callback. Inicie o login novamente."
        ),
        "access_denied": "O acesso à conta Google foi negado.",
    }
    message = messages.get(error_code, "Não foi possível autenticar com o Google.")
    return f"{message} Código OAuth: {error_code}."


@router.post("/login", response_model=schemas.AuthResponse)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    HU02 - Login do usuário.

    CA01 (Login): credenciais corretas -> autentica e retorna um token de sessão.
    CA02 (Conta inexistente): e-mail não cadastrado -> avisa e sugere o cadastro.
    Senha incorreta (conta existe): 401, sem revelar detalhes além do necessário.
    """
    user = crud.get_user_by_email(db, credentials.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos uma conta com este e-mail. Que tal se cadastrar?",
        )

    if not security.verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    return tokens.issue_token_pair(db, user)


@router.post("/refresh", response_model=schemas.AuthResponse)
def refresh_session(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Rotaciona o refresh token e devolve um novo par de tokens."""
    try:
        return tokens.rotate_refresh_token(db, payload.refresh_token)
    except tokens.InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido, expirado ou revogado.",
        ) from exc


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(
    payload: schemas.LogoutRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Revoga o refresh token da sessão atual."""
    crud.revoke_refresh_token(
        db,
        token_hash=security.hash_refresh_token(payload.refresh_token),
        user_id=current_user.user_id,
    )
    return schemas.MessageResponse(message="Logout realizado com sucesso.")


@router.post("/logout-all", response_model=schemas.MessageResponse)
def logout_all(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Revoga todas as sessões renováveis do usuário autenticado."""
    crud.revoke_all_refresh_tokens(db, current_user.user_id)
    return schemas.MessageResponse(message="Todas as sessões foram encerradas.")


@router.get("/me", response_model=schemas.UserOut)
def get_authenticated_user(current_user: CurrentUser):
    """Retorna o usuário identificado pelo access token."""
    return current_user


@router.get(
    "/google",
    name="google_login",
    summary="Login com Google (abra pelo link na descrição do Swagger)",
    description="""
Use o link abaixo para abrir o fluxo em uma nova aba:

<a href="/api/v1/auth/google" target="_blank"><strong>▶ Entrar com Google</strong></a>

O botão **Execute** não deve ser usado para esta rota, porque o Swagger executa
a requisição AJAX e navegadores não permitem que ela siga o redirecionamento
para o domínio de autenticação do Google.
""",
)
async def google_login(request: Request):
    """Inicia o fluxo OAuth 2.0/OpenID Connect no Google."""
    if not google_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login com Google não está configurado no servidor.",
        )

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or str(
        request.url_for("google_callback")
    )

    # Cookies não são compartilhados entre localhost e 127.0.0.1. Quando o
    # Swagger é aberto pelo endereço exibido pelo Uvicorn (127.0.0.1), primeiro
    # canonicalizamos o início do fluxo para o host usado pelo callback.
    callback_url = urlsplit(redirect_uri)
    local_hosts = {"localhost", "127.0.0.1"}
    if (
        request.url.hostname in local_hosts
        and callback_url.hostname in local_hosts
        and request.url.hostname != callback_url.hostname
    ):
        canonical_login_url = (
            f"{callback_url.scheme}://{callback_url.netloc}"
            f"{request.url_for('google_login').path}"
        )
        return RedirectResponse(canonical_login_url)

    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get(
    "/google/callback",
    response_model=schemas.AuthResponse,
    name="google_callback",
)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Valida o retorno do Google e emite o JWT usado pelo restante da API."""
    if not google_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login com Google não está configurado no servidor.",
        )

    try:
        google_token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning(
            "Falha no callback OAuth do Google: error=%s description=%s "
            "host=%s session_cookie=%s",
            getattr(exc, "error", "oauth_error"),
            getattr(exc, "description", None),
            request.url.hostname,
            "presente" if request.cookies.get("allinvest_oauth_session") else "ausente",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_oauth_error_detail(exc),
        ) from exc

    user_info = google_token.get("userinfo")
    if not user_info:
        try:
            user_info = await oauth.google.userinfo(token=google_token)
        except OAuthError as exc:
            logger.warning(
                "Falha ao obter perfil Google: error=%s description=%s",
                getattr(exc, "error", "oauth_error"),
                getattr(exc, "description", None),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_oauth_error_detail(exc),
            ) from exc

    email = user_info.get("email") if user_info else None
    if not email or user_info.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A conta do Google precisa ter um e-mail verificado.",
        )

    user = crud.get_user_by_email(db, email)
    if not user:
        name = user_info.get("name") or email.split("@", maxsplit=1)[0]
        user = crud.create_google_user(db, name=name, email=email)

    auth_response = tokens.issue_token_pair(db, user)
    frontend_callback = os.getenv("FRONTEND_AUTH_CALLBACK_URL")
    if frontend_callback:
        query = urlencode(
            {
                "access_token": auth_response.access_token,
                "refresh_token": auth_response.refresh_token,
                "token_type": auth_response.token_type,
                "expires_in": auth_response.expires_in,
            }
        )
        # O fragmento não é enviado ao servidor do frontend nem fica em logs HTTP.
        return RedirectResponse(f"{frontend_callback}#{query}")

    return auth_response
