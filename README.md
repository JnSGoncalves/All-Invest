# All Invest

Aplicação web para centralizar ações da B3. A pessoa cria uma conta, organiza seus investimentos em carteiras, registra compras e vendas e acompanha as posições consolidadas.

> **Lab 4 – Especificação de Interfaces e Contratos e Implementação de Componentes.**
> Componentes implementados (definidos no Lab 3): **Investment Component** e **Portfolio Component**.
> Documentos da entrega na raiz: [`Especificacao_Componentes.pdf`](Especificacao_Componentes.pdf),
> [`Roteiro_Video.pdf`](Roteiro_Video.pdf) e [`Relatorio_Implementacao.pdf`](Relatorio_Implementacao.pdf).

**Equipe:** Danilo Henrique de Paulo · Jônatas da Silva Gonçalves · Kaynã de Deus Ferreira da Silva · Pedro Henrique da Fonseca do Nascimento · Vinícius do Nascimento Generoso · Wallace dos Santos Izidoro

## Tecnologias utilizadas

| Camada | Tecnologias |
|---|---|
| Backend (componentes) | Python 3.12, FastAPI 0.141, Pydantic 2, SQLAlchemy 2.0 |
| Banco de dados | PostgreSQL (Supabase); SQLite em memória nos testes |
| Integração externa | brapi.dev (validação de ticker e cotação, via Market Data Component) |
| Testes | pytest 9, plugin anyio (testes assíncronos), `TestClient` do FastAPI |
| Frontend | React, TypeScript e Vite |
| Infraestrutura | Docker Compose, Nginx, GitHub Actions |

O frontend conversa com a API por um proxy. `API_KEY` fica no ambiente do servidor e não é incluída no JavaScript enviado ao navegador.

## Estrutura dos componentes

Recorte implementado da arquitetura do Lab 3: o **Investment Component** fornece `IInvestmentService` e requer `IPortfolioService`, que é fornecida pelo **Portfolio Component**.

```
          IInvestmentService                          IPortfolioService
                 O                                            O
                 |                                            |
  +--------------+--------------+    «requer»    +------------+---------------+
  |    Investment Component     |--------------->|    Portfolio Component     |
  |    (InvestmentService)      |  via interface |    (PortfolioService)      |
  +--------------+--------------+                +----------------------------+
                 | «requer» IMarketDataService (componente já existente)
                 v
       Market Data Component  ---->  brapi.dev (API de dados de mercado)
```

```
backend/
├── src/
│   ├── interfaces/components.py        # IPortfolioService e IInvestmentService (contratos)
│   ├── services/portfolio_service.py   # Portfolio Component (implementação)
│   ├── services/investment_service.py  # Investment Component (implementação)
│   ├── dependencies/components.py      # Liga as implementações às interfaces (injeção)
│   ├── routers/portfolios.py           # Endpoints /api/portfolios
│   ├── routers/stocks.py               # Endpoints /api/stocks
│   ├── db/crud.py, db/schemas.py       # Persistência e DTOs de entrada/saída
│   └── models.py                       # Tabelas, incluindo portfolios e portfolios_stocks
├── tests/                              # Testes unitários, de integração e de contrato
├── pytest.ini
└── requirements-dev.txt
database/migrations/002_create_portfolios.sql   # Tabelas do Portfolio Component
docs/evidencias/                                # Saída da execução dos testes
```

| Componente | Responsabilidade | Interface fornecida | Interfaces requeridas |
|---|---|---|---|
| Portfolio Component | Cadastrar, consultar, editar e remover carteiras; associar ativos a carteiras | `IPortfolioService` | Nenhuma (apenas a própria persistência) |
| Investment Component | Registrar compras e vendas, consolidar posições, associar e remover investimentos | `IInvestmentService` | `IPortfolioService`, `IMarketDataService` |

## Interfaces e operações implementadas

As interfaces são `typing.Protocol` em [`backend/src/interfaces/components.py`](backend/src/interfaces/components.py). Os contratos (pré e pós-condições) estão nas docstrings de cada operação e detalhados em `Especificacao_Componentes.pdf`.

### `IPortfolioService` (fornecida pelo Portfolio Component)

| Operação (Lab 3) | Método | Endpoint |
|---|---|---|
| criarCarteira() | `create_portfolio(user_id, portfolio_in)` | `POST /api/portfolios` |
| consultarCarteira() | `list_portfolios(user_id)`, `get_portfolio(user_id, portfolio_id)` | `GET /api/portfolios`, `GET /api/portfolios/{id}` |
| editarCarteira() | `update_portfolio(user_id, portfolio_id, portfolio_in)` | `PATCH /api/portfolios/{id}` |
| removerCarteira() | `delete_portfolio(user_id, portfolio_id)` | `DELETE /api/portfolios/{id}` |
| associarInvestimento() | `associate_investment(user_id, portfolio_id, stock_id)` | Chamada pelo Investment |
| Apoio à integração | `dissociate_investment(user_id, stock_id)`, `get_investment_portfolios(user_id)` | Chamadas pelo Investment |

### `IInvestmentService` (fornecida pelo Investment Component)

| Operação (Lab 3) | Método | Endpoint |
|---|---|---|
| cadastrarAcao() / registrarMovimentacao() | `create_trade(user_id, trade_in)` | `POST /api/stocks` (aceita `portfolio_id` opcional) |
| consultarInvestimentos() | `list_trades(user_id)`, `get_positions(user_id, portfolio_id=None)` | `GET /api/stocks`, `GET /api/stocks/carteira?portfolio_id=` |
| editarInvestimento() (associar ação à carteira) | `associate_position(user_id, stock_name, portfolio_id)` | `PUT /api/stocks/{ticker}/portfolio` |
| removerInvestimento() | `remove_position(user_id, stock_name)` | `DELETE /api/stocks/{ticker}` |

Todas as rotas exigem `X-API-Key` e `Authorization: Bearer <access_token>`. Uma carteira de outro usuário é tratada como inexistente (404).

## Como ocorre a comunicação entre os componentes

1. A comunicação acontece **dentro do mesmo processo, por interface**: o `InvestmentService` recebe no construtor um objeto do tipo `IPortfolioService` e não importa `PortfolioService`.
2. A ligação é feita em [`backend/src/dependencies/components.py`](backend/src/dependencies/components.py): `get_investment_service()` usa o `Depends` do FastAPI para criar o `PortfolioService` e entregá-lo ao `InvestmentService`. Os dois usam a mesma sessão de banco da requisição.
3. Pontos em que o Investment chama o Portfolio:
   - `create_trade` chama `get_portfolio` (valida a carteira **antes** de consultar a B3 e gravar) e, depois de gravar a operação, `associate_investment`;
   - `get_positions` chama `get_investment_portfolios` (preenche `portfolio_id`/`portfolio_name` e filtra por carteira);
   - `associate_position` chama `associate_investment`;
   - `remove_position` chama `dissociate_investment`.
4. Os erros de contrato do Portfolio (por exemplo, 404 para carteira inexistente) chegam sem alteração à resposta HTTP.

Fluxo de `POST /api/stocks` com `portfolio_id`:

```
Cliente -> routers/stocks.py -> IInvestmentService.create_trade
           -> IPortfolioService.get_portfolio         (a carteira é do usuário?)
           -> IMarketDataService.validate_ticker      (o ticker existe na B3?)
           -> grava users_stocks
           -> IPortfolioService.associate_investment  (grava portfolios_stocks)
```

## Testes realizados

Os testes ficam em [`backend/tests/`](backend/tests/). Eles usam SQLite em memória e um stub do Market Data, não acessam o Supabase nem a brapi.dev e não precisam do `.env`.

| Arquivo | Tipo | O que verifica |
|---|---|---|
| `test_portfolio_component.py` | Unitário (Portfolio) | Criar, listar, consultar, editar e remover carteira; nome duplicado (409); isolamento entre usuários (404); associar, mover e desassociar ativo; validação dos DTOs |
| `test_investment_component.py` | Unitário (Investment com stub de `IPortfolioService`) | Registrar compra/venda; cotação automática; ticker inválido (404); corretora inválida (400); venda acima do saldo (422); preço médio; filtro por carteira; associar e remover investimento; chamadas feitas à interface do Portfolio |
| `test_integration_investment_portfolio.py` | Integração (componentes reais) | Operação com carteira associa o ativo; mover ativo entre carteiras; posições por carteira; remover carteira preserva as operações; remover investimento desfaz a associação; carteira de outro usuário é recusada |
| `test_api_integration.py` | Integração ponta a ponta (HTTP) | Fluxo pelas rotas: criar carteira, registrar compra com carteira, consultar por carteira, mover, editar e remover; erros 404, 409, 422 e API key inválida (401) |
| `test_interface_contracts.py` | Contrato | As implementações expõem todas as operações das interfaces, com a mesma assinatura e o mesmo modo (síncrono/assíncrono); o Investment requer `IPortfolioService` |

Resultado atual: **45 testes aprovados**. A saída completa está em [`docs/evidencias/resultado_testes.txt`](docs/evidencias/resultado_testes.txt), com versão JUnit XML no mesmo diretório. O workflow [`tests.yml`](.github/workflows/tests.yml) executa os testes a cada push.

### Executar os testes

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -v                                      # todos
python -m pytest tests/test_portfolio_component.py -v    # somente o Portfolio
python -m pytest tests/test_investment_component.py -v   # somente o Investment
python -m pytest tests/test_integration_investment_portfolio.py tests/test_api_integration.py -v   # integração
```

## Instruções para execução

### Pré-requisitos

- Node.js 22 ou mais recente.
- Python 3.12.
- Um banco PostgreSQL/Supabase acessível pela `DATABASE_URL`.
- A chave da aplicação cadastrada na tabela `api_keys`.
- Um token BRAPI para validar tickers e obter cotações.

### Preparar o banco e as variáveis

1. No SQL Editor do Supabase, execute [`database/CreateTables.sql`](database/CreateTables.sql) para criar as tabelas (se ainda não existirem).
   Em um banco criado antes do Lab 4, execute apenas [`database/migrations/002_create_portfolios.sql`](database/migrations/002_create_portfolios.sql). Ela cria `portfolios` e `portfolios_stocks` sem alterar as tabelas existentes.
2. Copie e preencha os arquivos locais de ambiente:

   ```powershell
   Copy-Item backend/.env.example backend/.env -Force
   Copy-Item frontend/.env.example frontend/.env -Force
   ```

3. Em `backend/.env`, configure `DATABASE_URL`, `BRAPI_TOKEN`, `SECRET_KEY` e `SESSION_SECRET_KEY`. `API_KEY` precisa corresponder a um valor armazenado em `api_keys.api_key`; se a tabela estiver vazia, gere uma chave e cadastre o mesmo valor em `frontend/.env` e no banco:

   ```powershell
   $apiKey = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
   $apiKey
   ```

   ```sql
   INSERT INTO api_keys (project_name, api_key)
   VALUES ('All Invest', '<cole-a-chave-gerada-aqui>');
   ```

   Não compartilhe nem versione os arquivos `.env`.
4. Configure `API_KEY` em `frontend/.env` com a chave existente em `api_keys.api_key`. No desenvolvimento com Vite, se essa variável estiver vazia, o proxy tenta lê-la de `backend/.env`. Não use prefixo `VITE_` na chave.
5. Se quiser habilitar o acesso com Google, configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` e `FRONTEND_AUTH_CALLBACK_URL` no backend, autorize a URI de callback no Google Cloud e defina `VITE_GOOGLE_ENABLED=true` em `frontend/.env` (e no `.env` da raiz para Docker). O cadastro e o login por e-mail não dependem do Google.

A API não inicia com persistência funcional até que a conexão com o banco e as chaves acima sejam preenchidas.

### Executar localmente (PowerShell)

No primeiro terminal, na raiz do repositório:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

No segundo terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Abra <http://localhost:5173>. O Vite encaminha `/api/*` para `API_URL` (padrão `http://localhost:8000`) e adiciona a chave somente no servidor. A documentação da API fica em <http://localhost:8000/docs>; as rotas dos dois componentes aparecem nos grupos **portfolios** e **stocks**.

O formulário de cadastro cria o usuário em `POST /api/users` e inicia a sessão. O painel usa `GET /api/stocks/carteira`; o formulário registra compra/venda em `POST /api/stocks`. Excluir uma posição remove as movimentações daquele ticker da carteira do usuário.

### Executar com Docker

Configure `backend/.env` como acima e execute na raiz:

```powershell
Copy-Item .env.example .env -Force
# Confirme que frontend/.env contém a API_KEY registrada na tabela api_keys.
docker compose up --build
```

O serviço backend lê `backend/.env`; o container Nginx lê `API_KEY` diretamente de `frontend/.env` e a envia somente pelo proxy interno.

Abra <http://localhost:4671> para o frontend e <http://localhost:4670/docs> para a API. O container do frontend encaminha `/api/*` ao backend pela rede interna do Docker.

## Funcionalidades incluídas

- Cadastro de usuário e login por e-mail/senha.
- Login com Google opcional, quando as credenciais OAuth estão configuradas.
- Sessão com access token e renovação automática usando refresh token.
- Carteira por usuário com resumo de posições e preço médio.
- Registro de compra e venda com validação do ticker pela BRAPI.
- Carteiras do usuário (criar, listar, editar e remover) e associação de cada ativo a uma carteira.
- Consulta das posições filtrada por carteira.
- Remoção de um ticker e de seu histórico de movimentações da carteira autenticada.

Ao remover um ticker, o backend apaga todas as operações daquele ticker pertencentes ao usuário atual e desfaz a associação com a carteira. A operação exige confirmação na interface.
