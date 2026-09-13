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
2. Para testar localmente sem PostgreSQL, não é necessário configurar nada: a API usa o arquivo SQLite `all_invest.db` por padrão.
  Se preferir deixar isso explícito, crie um `.env` com:
  ```env
  DATABASE_URL=sqlite:///./all_invest.db
  ```
  Para usar PostgreSQL, copie `.env.example` para `.env` e ajuste a `DATABASE_URL`.
3. Suba a API:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Docs interativas em `http://localhost:8000/docs`.

No Windows PowerShell, ative o ambiente virtual com:
```powershell
.\venv\Scripts\Activate.ps1
```

O SQLite é suficiente para os testes locais. O arquivo `all_invest.db` é criado
automaticamente na pasta do projeto e pode ser removido para começar novamente
com um banco vazio. Em produção ou no uso integrado da equipe, prefira
PostgreSQL.

Na primeira execução, `Base.metadata.create_all()` cria as tabelas automaticamente
a partir dos models. Para um projeto mais maduro, vale migrar para Alembic.

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

