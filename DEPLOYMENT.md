# Execução e publicação

## Desenvolvimento sem Docker

Backend, a partir de `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --port 8000
```

Frontend, em outro terminal, a partir de `frontend/`:

```powershell
Copy-Item .env.example .env
npm ci
npm run dev
```

Abra `http://localhost:5173`. O Google retorna para o backend em
`http://localhost:8000/api/v1/auth/google/callback`, e o backend conclui em
`http://localhost:5173/auth/callback`.

## Desenvolvimento com Docker

Na raiz do projeto:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

Frontend: `http://localhost:4671`. API: `http://localhost:4670/docs`.

## Produção

1. Configure `API_KEY` em `frontend/.env` com o valor cadastrado em `api_keys.api_key`. O Compose passa esse arquivo ao container Nginx.
2. Copie `backend/.env.production.example` para `backend/.env` no servidor e
   preencha as credenciais privadas: banco, Google client secret, `SECRET_KEY`
   e `SESSION_SECRET_KEY`.
3. No Google Cloud, autorize exatamente:
   `https://allinvest-api.ojota.dev.br/api/v1/auth/google/callback`.
4. Gere e suba os containers:

```bash
docker compose --env-file .env.production up -d --build
```

5. Encaminhe os domínios no proxy reverso. A interface chama `/api/*` no mesmo host e o Nginx do container frontend encaminha essas chamadas ao backend, adicionando `API_KEY` apenas no servidor:

```nginx
server {
    server_name allinvest.ojota.dev.br;
    location / {
        proxy_pass http://127.0.0.1:4671;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

server {
    server_name allinvest-api.ojota.dev.br;
    location / {
        proxy_pass http://127.0.0.1:4670;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Ative HTTPS para ambos os hosts antes de testar o OAuth. `API_KEY` é lida de
`frontend/.env` em tempo de execução; ela não é incorporada ao build.
