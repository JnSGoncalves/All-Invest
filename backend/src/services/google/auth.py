import os

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

load_dotenv()

# A instância OAuth é compartilhada pela aplicação principal. As variáveis
# CLIENT_ID/CLIENT_SECRET são mantidas como fallback para não quebrar ambientes
# que já usavam os nomes antigos.
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID") or os.getenv("CLIENT_ID"),
    client_secret=(
        os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
    ),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)


def google_is_configured() -> bool:
    """Informa se as credenciais mínimas do Google foram configuradas."""
    return bool(
        (os.getenv("GOOGLE_CLIENT_ID") or os.getenv("CLIENT_ID"))
        and (os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("CLIENT_SECRET"))
    )
