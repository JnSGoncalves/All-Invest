# Autenticação da API

Base URL: `/api/v1/auth`.

## Endpoints de autenticação

- `POST /login`: exige `X-API-Key`; autentica e devolve usuário, access token e
  refresh token.
- `POST /refresh`: exige `X-API-Key`; rotaciona um refresh token válido. O token
  anterior deixa de funcionar imediatamente.
- `GET /google` e `GET /google/callback`: iniciam e concluem o OpenID Connect.
  São as únicas rotas de auth dispensadas da API key porque o redirecionamento
  do navegador e a chamada de retorno do Google não enviam esse cabeçalho.

## Endpoints autenticados

- `GET /me`: retorna o usuário do access token.
- `POST /logout`: exige Bearer e o refresh token no body; revoga a sessão.
- `POST /logout-all`: exige Bearer; revoga todas as sessões renováveis do usuário.

Resposta de login/refresh:

```json
{
  "access_token": "jwt",
  "refresh_token": "segredo-opaco",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "user_id": 1,
    "name": "Nome",
    "email": "usuario@example.com",
    "created_at": "2026-09-19T12:00:00Z"
  }
}
```

O access token é um JWT assinado e de curta duração. O refresh token é aleatório;
somente seu hash SHA-256 é persistido em `refresh_tokens`.

## Proteger endpoints futuros

Use o alias tipado `CurrentUser`:

```python
from ..dependencies.auth import CurrentUser

@router.get("/carteira")
def obter_carteira(current_user: CurrentUser):
    return {"user_id": current_user.user_id}
```

Ou use a função explicitamente com `Depends`:

```python
from fastapi import Depends
from ..dependencies.auth import get_current_user

@router.get("/carteira")
def obter_carteira(current_user=Depends(get_current_user)):
    return {"user_id": current_user.user_id}
```

Todos os endpoints exigem `X-API-Key` pelo middleware global, exceto health,
documentação e as duas rotas de redirecionamento Google descritas acima. As
rotas `/me` e `/logout*` exigem também Bearer pela dependência; `/login` e
`/refresh` exigem a API key mesmo sem sessão de usuário.

## Variáveis

```ini
SECRET_KEY=<chave longa e aleatória>
SESSION_SECRET_KEY=<outra chave longa e aleatória>
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ORIGINS=http://localhost:5173,http://localhost:4671
```

Após alterar o schema, aplique `migrations/001_fix_refresh_tokens.sql`. No banco
atual ela já foi aplicada.
