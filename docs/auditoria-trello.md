# Auditoria Trello × implementação — 31/10/2026

Quadro: [Gestão de projetos - FEI](https://trello.com/b/KCYFRVeZ). Identificado pelas histórias HU01–HU11 e pelo nome All Invest nos cartões. Foram lidas todas as listas, as descrições completas dos 33 cartões de Concluído e seus 30 checklists (112 itens), sem paginação ou truncamento pendente. Não havia comentários nesses cartões.

| Lista solicitada | Cartões abertos |
|---|---:|
| Em andamento | 0 |
| Teste | 0 |
| Concluído | 33 |

Os estados do Trello eram declarações da equipe; foram comparados com o código. O Product Backlog e o Sprint Backlog foram lidos para contextualizar os critérios de aceite, mas não tratados como novos pedidos. Os cartões e checklists no Trello não foram alterados.

## Lacunas corrigidas

- HU03/HU04: telas de cadastro e listagem de corretoras ausentes, apesar de os endpoints já existirem. Adicionadas mensagens de confirmação, validação junto ao campo, estado vazio e integração com o cadastro de ações usando IDs reais e `broker_source=registered`.
- HU08: faltavam histórico com cache, cálculo por período, rota e tela. Implementados como serviço com contrato e injeção de dependências, seguindo a organização existente.
- HU01: confirmação de senha e mensagem de sucesso ausentes; nome contendo só espaços era aceito pela API. Corrigidos e cobertos por testes.
- HU02: a renovação de uma sessão persistida em SQLite falhava ao comparar datas com e sem fuso. Normalizada a leitura UTC, com testes de rotação, expiração e reutilização.
- Datas das movimentações normalizadas para UTC na gravação; o período é avaliado por dia em America/Sao_Paulo.
- Corrigido excesso de largura no celular: o texto acessível da tabela escapava do contêiner de rolagem. O teste agora verifica que a página cabe em 390 px.
- Workflow ampliado para executar análise, compilação e testes do navegador junto ao backend.

## Conferência individual dos cartões

Os caminhos de código abaixo são relativos à raiz; testes `test_*.py` ficam em `backend/tests` e `*.spec.ts` em `frontend/tests`.

| Cartão | Resultado | Evidências | Conferência |
|---|---|---|---|
| [Integração com API de cotações históricas - HU08](https://trello.com/c/xvxGeQAs) | Implementado nesta auditoria | `performance_service.py`, `market_data_service.py`, `PerformancePanel.tsx`; `test_performance_component.py`, `test_performance_api.py`, `test_market_history.py`, `flows.spec.ts` | Histórico diário com cache, cálculo por ativo e carteira, período inclusivo, estados vazio/erro e integração HTTP. |
| [Testes de integração - HU08](https://trello.com/c/tbBQGYuj) | Implementado nesta auditoria | `performance_service.py`, `market_data_service.py`, `PerformancePanel.tsx`; `test_performance_component.py`, `test_performance_api.py`, `test_market_history.py`, `flows.spec.ts` | Histórico diário com cache, cálculo por ativo e carteira, período inclusivo, estados vazio/erro e integração HTTP. |
| [Listagem de corretoras no Front-End - HU04](https://trello.com/c/CiCRPrIP) | Implementado nesta auditoria | `BrokerPanel.tsx`, `Home.tsx`, `api.ts`; `flows.spec.ts` | GET/POST reais, mensagem vazia de CA02, validação junto ao campo, confirmação e uso dos IDs cadastrados nas ações. |
| [Endpoint de Listagem de Corretoras - HU04](https://trello.com/c/kaJH8iJy) | Existente e validado | `routers/brokers.py`, `services/broker_service.py`, `models.py`; `test_api_integration.py`, `flows.spec.ts` | API autenticada, persistência do vínculo, duplicidade, entradas inválidas e isolamento entre usuários. |
| [HU01 - Cadastro de usuário](https://trello.com/c/fia8oSzy) | Existente; cadastro complementado e validado | `Login.tsx`, `schemas.py`, `routers/users.py`, `db/crud.py`; `test_user_auth_api.py`, `flows.spec.ts` | Confirmação de senha e mensagem de sucesso adicionadas; nome em branco recusado. Cadastro, hash, login e conta duplicada validados. |
| [HU02 - Login do usuário](https://trello.com/c/zG7gQoIu) | Existente; sessão corrigida e validada | `Login.tsx`, `routers/auth.py`, `services/tokens.py`, OAuth; `test_user_auth_api.py`, `test_api_integration.py`, `flows.spec.ts` | Login, conta inexistente, senha inválida, OAuth simulado, renovação persistida, token vencido/reutilizado e recarga do navegador. |
| [HU07 - Cadastrar ações](https://trello.com/c/CgyQEUmm) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Integração | B3 e Front-end - HU07](https://trello.com/c/tZOiMw31) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Criar formulário de cadastro - HU01](https://trello.com/c/OS3WrdxX) | Existente; cadastro complementado e validado | `Login.tsx`, `schemas.py`, `routers/users.py`, `db/crud.py`; `test_user_auth_api.py`, `flows.spec.ts` | Confirmação de senha e mensagem de sucesso adicionadas; nome em branco recusado. Cadastro, hash, login e conta duplicada validados. |
| [Criar formulário de cadastro de ações - HU07](https://trello.com/c/Lfu9W3Gw) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Validação Cadastro de ações - HU07](https://trello.com/c/Bv7juMmW) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Criar formulário de login - HU02](https://trello.com/c/dC67UnGC) | Existente; sessão corrigida e validada | `Login.tsx`, `routers/auth.py`, `services/tokens.py`, OAuth; `test_user_auth_api.py`, `test_api_integration.py`, `flows.spec.ts` | Login, conta inexistente, senha inválida, OAuth simulado, renovação persistida, token vencido/reutilizado e recarga do navegador. |
| [Modelagem dos dados](https://trello.com/c/voSrrA7E) | Existente e validado | `models.py`, `database/CreateTables.sql`, migrações 002/003; testes de componentes e integração | Usuários, hash de senha, ações, operações com datas e corretoras, carteiras e associações persistidos. |
| [Endpoint de Cadastro - HU07](https://trello.com/c/C9EKZBub) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Implementação de API externa - HU07](https://trello.com/c/lGT5LGSE) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Integrar API externa OAuth 2.0 - HU02](https://trello.com/c/3hhFeSNf) | Existente; sessão corrigida e validada | `Login.tsx`, `routers/auth.py`, `services/tokens.py`, OAuth; `test_user_auth_api.py`, `test_api_integration.py`, `flows.spec.ts` | Login, conta inexistente, senha inválida, OAuth simulado, renovação persistida, token vencido/reutilizado e recarga do navegador. |
| [Persistência de Ações - HU07](https://trello.com/c/0w1E2Hop) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Validação do Cadastro - HU01](https://trello.com/c/2jHm8LGw) | Existente; cadastro complementado e validado | `Login.tsx`, `schemas.py`, `routers/users.py`, `db/crud.py`; `test_user_auth_api.py`, `flows.spec.ts` | Confirmação de senha e mensagem de sucesso adicionadas; nome em branco recusado. Cadastro, hash, login e conta duplicada validados. |
| [Persistência do Usuário - HU01](https://trello.com/c/k8w0IdRH) | Existente; cadastro complementado e validado | `Login.tsx`, `schemas.py`, `routers/users.py`, `db/crud.py`; `test_user_auth_api.py`, `flows.spec.ts` | Confirmação de senha e mensagem de sucesso adicionadas; nome em branco recusado. Cadastro, hash, login e conta duplicada validados. |
| [Criar endpoint na API - HU02](https://trello.com/c/3wrnjS7i) | Existente; sessão corrigida e validada | `Login.tsx`, `routers/auth.py`, `services/tokens.py`, OAuth; `test_user_auth_api.py`, `test_api_integration.py`, `flows.spec.ts` | Login, conta inexistente, senha inválida, OAuth simulado, renovação persistida, token vencido/reutilizado e recarga do navegador. |
| [Verificação de Conta Existente - HU01](https://trello.com/c/QRbdtlgO) | Existente; cadastro complementado e validado | `Login.tsx`, `schemas.py`, `routers/users.py`, `db/crud.py`; `test_user_auth_api.py`, `flows.spec.ts` | Confirmação de senha e mensagem de sucesso adicionadas; nome em branco recusado. Cadastro, hash, login e conta duplicada validados. |
| [Listagem de ações cadastradas no Front-End - HU07](https://trello.com/c/OlJr1CNj) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Endpoint de Listagem - HU07](https://trello.com/c/XFDOFi5D) | Existente; integração com corretoras complementada | `investment_service.py`, `routers/stocks.py`, `Home.tsx`; testes de investimento, API, integração e `pagination.spec.ts`/`flows.spec.ts` | Cadastro B3, listagem paginada, persistência, preços/quantidades válidos, estados de erro e cadastro com corretora real. Operações normalizadas em UTC. |
| [Endpoint de Cadastro - HU01](https://trello.com/c/kLow9CMJ) | Existente; cadastro complementado e validado | `Login.tsx`, `schemas.py`, `routers/users.py`, `db/crud.py`; `test_user_auth_api.py`, `flows.spec.ts` | Confirmação de senha e mensagem de sucesso adicionadas; nome em branco recusado. Cadastro, hash, login e conta duplicada validados. |
| [Integrar login à API - HU02](https://trello.com/c/YPK2EBsI) | Existente; sessão corrigida e validada | `Login.tsx`, `routers/auth.py`, `services/tokens.py`, OAuth; `test_user_auth_api.py`, `test_api_integration.py`, `flows.spec.ts` | Login, conta inexistente, senha inválida, OAuth simulado, renovação persistida, token vencido/reutilizado e recarga do navegador. |
| [Endpoint de Cadastro de Corretora - HU03](https://trello.com/c/O1Sral2F) | Existente e validado | `routers/brokers.py`, `services/broker_service.py`, `models.py`; `test_api_integration.py`, `flows.spec.ts` | API autenticada, persistência do vínculo, duplicidade, entradas inválidas e isolamento entre usuários. |
| [Persistência da Corretora - HU03](https://trello.com/c/kvhBqiLO) | Existente e validado | `routers/brokers.py`, `services/broker_service.py`, `models.py`; `test_api_integration.py`, `flows.spec.ts` | API autenticada, persistência do vínculo, duplicidade, entradas inválidas e isolamento entre usuários. |
| [Criar formulário de cadastro de corretora - HU03](https://trello.com/c/5MUueIcC) | Implementado nesta auditoria | `BrokerPanel.tsx`, `Home.tsx`, `api.ts`; `flows.spec.ts` | GET/POST reais, mensagem vazia de CA02, validação junto ao campo, confirmação e uso dos IDs cadastrados nas ações. |
| [Endpoint de Rendimento por Período - HU08](https://trello.com/c/A5MGfrTf) | Implementado nesta auditoria | `performance_service.py`, `market_data_service.py`, `PerformancePanel.tsx`; `test_performance_component.py`, `test_performance_api.py`, `test_market_history.py`, `flows.spec.ts` | Histórico diário com cache, cálculo por ativo e carteira, período inclusivo, estados vazio/erro e integração HTTP. |
| [Tela de Rendimentos com seleção de período - HU08](https://trello.com/c/EiEbDeTj) | Implementado nesta auditoria | `performance_service.py`, `market_data_service.py`, `PerformancePanel.tsx`; `test_performance_component.py`, `test_performance_api.py`, `test_market_history.py`, `flows.spec.ts` | Histórico diário com cache, cálculo por ativo e carteira, período inclusivo, estados vazio/erro e integração HTTP. |
| [Avaliar fonte de cotações históricas (Brapi x yfinance) - HU08](https://trello.com/c/6PRfm1ht) | Decisão existente preservada; contrato implementado | `backend/src/services/market_data_service.py`; documentação oficial BRAPI; `test_market_history.py` | A decisão do cartão já escolhe BRAPI. Consulta por datas, preços originais e limitações documentados; cobertura/plano reais não aferidos. |
| [Validação do Cadastro de Corretora - HU03](https://trello.com/c/vqjyXSZU) | Existente e validado | `routers/brokers.py`, `services/broker_service.py`, `models.py`; `test_api_integration.py`, `flows.spec.ts` | API autenticada, persistência do vínculo, duplicidade, entradas inválidas e isolamento entre usuários. |
| [Cálculo de rendimento da carteira - HU08](https://trello.com/c/BzmVr18g) | Implementado nesta auditoria | `performance_service.py`, `market_data_service.py`, `PerformancePanel.tsx`; `test_performance_component.py`, `test_performance_api.py`, `test_market_history.py`, `flows.spec.ts` | Histórico diário com cache, cálculo por ativo e carteira, período inclusivo, estados vazio/erro e integração HTTP. |

## Contrato e método de cálculo da HU08

`GET /api/stocks/rendimentos?start=2026-09-01&end=2026-09-30` exige API key e sessão Bearer. Datas são obrigatórias, inclusivas, não futuras e limitadas a 3660 dias, com início a partir de 11/01/1970. O contrato tipado é `PerformanceOut`: datas, `has_assets`, lista por ativo, valores inicial/final, compras, vendas, proventos, ganho e percentual. Sem ativos no período, retorna 200, lista vazia, ganho zero e percentual nulo.

A abertura considera a quantidade existente antes do primeiro dia, pelo fechamento anterior; o encerramento considera todas as operações até o último dia. Usa-se o fechamento mais recente até a data de avaliação, com tolerância máxima de sete dias para fins de semana e feriados; ausência de preço resulta em erro explícito, sem estimativas silenciosas.

```text
ganho = valor_final - valor_inicial - compras + vendas + proventos_registrados
percentual = 100 × ganho / (valor_inicial + compras)
```

O percentual é uma razão simples sobre o capital inicial mais compras, não TWR, TIR ou retorno anualizado. Quando a base é zero, o percentual é nulo. O total é a soma dos ativos; posições encerradas no período mantêm o ganho realizado. Operações posteriores ao fim e registros de outros usuários são excluídos. Proventos preservados após exclusão de operações continuam considerados no período de recebimento.

Exemplo conferido manualmente nos testes: 10 ações iniciais a R$ 22; compra de 5 a R$ 25; venda de 4 a R$ 30; 11 ações finais a R$ 28; R$ 10 em proventos. Ganho: 308 − 220 − 125 + 120 + 10 = R$ 93; percentual: 26,9565% sobre R$ 345.

## Fonte e limites da validação

A decisão registrada no [cartão da fonte](https://trello.com/c/6PRfm1ht) escolhe BRAPI. A integração usa `/api/v2/stocks/historical`, `startDate/endDate`, `interval=1d` e `includeRaw=true`, conforme a [documentação oficial](https://brapi.dev/docs/acoes/historico). A BRAPI pode ajustar `close`; por isso são exigidos `rawClose` positivos e finitos para valorar quantidades reais sem contar proventos duas vezes. O recurso `includeRaw` exige plano Pro na documentação consultada. Falta de acesso/cobertura retorna erro explicativo. Nenhum plano foi contratado ou alterado.

Cache em memória por provedor, ticker e datas, com TTL de 15 minutos e limite de 256 consultas. Erros não são armazenados e respostas não podem alterar os objetos do cache. Cada processo mantém seu cache; não há persistência compartilhada entre réplicas.

As chamadas externas são simuladas nos testes, inclusive erros 400/401/403/404/429/500, timeout, conexão e dados inválidos. O navegador usa API, JWT, renovação e banco reais em ambiente temporário; somente o provedor de mercado é substituído. OAuth usa provedor simulado nos testes existentes. Não foram acessados Supabase, contas Google ou BRAPI com credenciais reais, nem aplicado SQL em produção. Cobertura de tickers e permissões do plano do usuário dependem de validação operacional.

O cálculo usa as quantidades e os proventos registrados pelo usuário. Não importa automaticamente desdobramentos, grupamentos, taxas ou impostos; o histórico deve refletir esses eventos para representar corretamente tais situações.

## Validação reproduzível

- Backend: `python -m pytest -v` na pasta backend; saída completa e JUnit em `docs/evidencias/resultado_testes.txt` e `resultado_testes.xml`.
- Interface: `npm run lint`, `npm run build`, `npx playwright test` na pasta frontend.
- Playwright inicia Vite (4175) e API isolada (8175), com banco temporário, sem segredos locais. Use `BACKEND_PYTHON` para indicar o Python com dependências; no Windows reconhece `../venv/Scripts/python.exe`. Localmente usa Edge; no CI usa Chromium.
- Capturas: `docs/evidencias/carteira-desktop.png` e `carteira-mobile.png`.

Resultados finais: **112 testes de backend e 4 testes de navegador aprovados**. `npm run build`, `npm run lint` e `git diff --check` concluídos sem erros. A execução do navegador está em `docs/evidencias/resultado_frontend.txt`. As capturas de computador e celular foram inspecionadas visualmente. O workflow foi atualizado, mas não foi executado remotamente nesta auditoria. Avisos de descontinuação das dependências existentes não representam falhas dos testes.

