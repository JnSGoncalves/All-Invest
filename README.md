# All Invest — API (HU01: Cadastro de usuário)

API em FastAPI + SQLAlchemy para o HUB de investimentos All Invest.

## Estrutura

```
app/
  database.py    # engine, sessão e Base do SQLAlchemy
  models.py      # tabelas do MER (users, stocks, brokers, users_stocks, users_brokers)
  schemas.py     # UserCreate / UserOut (Pydantic)
  security.py    # hash e verificação de senha (bcrypt)
  crud.py        # get_user_by_email, create_user
  routers/
    users.py     # POST /users
    auth.py      # POST /auth/login
  main.py        # instancia o FastAPI e registra as rotas
requirements.txt
.env.example
```

## Como rodar

1. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure o Supabase: copie `.env.example` para `.env` e substitua `DATABASE_URL` pela connection string PostgreSQL exibida em `Project Settings > Database > Connection string`.
  Mantenha `?sslmode=require` na URL para exigir conexão TLS.
3. No SQL Editor do Supabase, execute o conteúdo de [`database/CreateTables.sql`](database/CreateTables.sql) uma vez para criar as tabelas.
4. Suba a API:
   ```bash
  uvicorn backend.src.main:app --reload
   ```
4. Docs interativas em `http://localhost:8000/docs`.

No Windows PowerShell, ative o ambiente virtual com:
```powershell
.\venv\Scripts\Activate.ps1
```

O backend usa exclusivamente PostgreSQL no Supabase. As tabelas não são criadas
automaticamente pela API: o schema versionado em `database/CreateTables.sql` deve
ser aplicado no SQL Editor do projeto. Para alterações futuras, vale migrar esse
script para Alembic.

## Endpoint implementado

### `POST /users`

Cadastra um novo usuário.

**Request body:**
```json
{
  "name": "Kaynã",
  "email": "kayna@example.com",
  "password": "senha_com_8_ou_mais_caracteres"
}
```

**Respostas:**
- `201 Created` — usuário criado, retorna `user_id`, `name`, `email`, `created_at` (nunca a senha/hash).
- `409 Conflict` — CA02: já existe conta com esse e-mail.
- `422 Unprocessable Entity` — validação do Pydantic (e-mail inválido, senha curta, etc.) — cobre a parte de validação de formato da HU01.

A senha nunca é armazenada em texto puro: é hasheada com `bcrypt` antes de ir para o banco.

### `POST /auth/login` — Login (HU02)

Autentica um usuário já cadastrado.

**Request body:**
```json
{
  "email": "kayna@example.com",
  "password": "senha_com_8_ou_mais_caracteres"
}
```

**Respostas:**
- `200 OK` — CA01: credenciais corretas, retorna `{ "access_token": "...", "token_type": "bearer" }` (JWT válido por 60 minutos).
- `404 Not Found` — CA02: e-mail não cadastrado, sugere o cadastro.
- `401 Unauthorized` — conta existe, mas a senha está incorreta.

O token gerado é auto-contido (JWT assinado com `SECRET_KEY`, sem depender de provedor externo) —
resolve o "gerenciamento de sessão via REST" da história sem entrar em OAuth 2.0, que fica para a
tarefa "Integrar API externa OAuth 2.0 - HU02" mais adiante. Defina `SECRET_KEY` no `.env` em produção.

