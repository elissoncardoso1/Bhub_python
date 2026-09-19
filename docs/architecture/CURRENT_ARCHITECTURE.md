# Arquitetura Atual — BHUB Backend

**Este é o documento de referência da arquitetura ATUAL.** Ele descreve somente o que
existe no repositório hoje, com evidência (`arquivo:linha`). Se algo aqui divergir do
código, o código está certo e este documento precisa de conserto.

- Repositório: `Bhub_py` · aplicação: `bhub-backend-python/` (FastAPI, Python 3.12+).
- Baseline desta versão do documento: commit `399915d` (branch `feat/v1.1-reliability`).
- Decisões estruturais: [`docs/adr/`](../adr/) — ADR-0001 (banco), ADR-0002 (fila de jobs),
  ADR-0003 (busca), ADR-0004 (monolito modular), ADR-0005 (estratégia de IA).
- Plano de trabalho em curso: `docs/superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md`.
- Documentos antigos que descrevem uma arquitetura anterior estão em
  [HISTORICAL](#historical) — **não** os use como descrição do presente.

## Como ler este documento

As seções abaixo (1 a 10) descrevem **somente o estado implementado** — o que existe e o
que foi verificado com infraestrutura real. Nada de plano, nada de intenção, entra nelas.
Os outros quatro blocos são separados de propósito e **nunca** se misturam com o presente:

| Bloco | Significa |
|---|---|
| **CURRENT** (seções 1–10) | Existe no repositório e foi exercitado. |
| **PLANNED** (seção 11) | Desejado e não implementado. |
| **DEFERRED** (seção 12) | Existe, foi reconhecido como insuficiente e a correção foi adiada por decisão explícita. |
| **KNOWN RISKS** (seção 13) | Existe hoje e é sabidamente defeituoso ou frágil. **Registrado, não corrigido.** |
| **HISTORICAL** (seção 14) | Documentação anterior a esta arquitetura. |

---

## 1. Componentes (CURRENT)

Monolito modular FastAPI. Cada camada tem uma responsabilidade e uma direção de
dependência.

| Componente | Caminho | Papel |
|---|---|---|
| Aplicação / lifespan | `app/main.py` | monta o `FastAPI`, registra o lifespan, middlewares, routers, `/health`, `/api/v1/cron/sync`, handlers de exceção |
| API REST JSON | `app/api/v1/`, `app/api/auth/` | endpoints `/api/v1/*` (articles, categories, authors, search, feeds, banners, ai, analytics, opengraph, contact, csrf, cookie_consent, admin/*) |
| Web SSR | `app/web/` | Jinja2 + HTMX; `app/web/router.py` inclui os routers `auth`, `admin`, `public`, `consent`, `translation` |
| Serviços | `app/services/` | regra de negócio: ingestão, classificação, busca, PDF, scraping, Open Graph, analytics, cache de tradução, dispatcher de tarefas |
| IA | `app/ai/` | `AIManager` e provedores (DeepSeek, OpenRouter, HuggingFace, LLM local) |
| ML local | `app/ml/` | `EmbeddingClassifier`, `HeuristicClassifier`, `ImpactRatingService` |
| Modelos | `app/models/` | SQLAlchemy 2.0 async (`Mapped[T]`/`mapped_column`) |
| Schemas | `app/schemas/` | Pydantic v2 |
| Núcleo | `app/core/` | segurança, CSRF, middlewares, rate limiting, logging, telemetria, alertas, lock do scheduler, anonimização de IP |
| Jobs | `app/jobs/` | `tasks.py` (worker ARQ), `scheduler.py` (APScheduler), `observe.py` (observabilidade de job) |
| Contratos | `app/interfaces/` | `services.py` (`IClassificationService`, `ISearchService`, `IFeedAggregator`, `IAIManager`), `task_queue.py` (`ITaskQueue`, `ArqTaskQueue`, `InlineTaskQueue`) |
| Migrações | `alembic/versions/` | 10 revisões versionadas; head = `009_feed_http_cache` (`tests/integration/conftest.py:59`) |
| Testes | `tests/` | suíte unitária (SQLite em memória) + `tests/integration/` (containers reais) + `tests/ci/ratchet_step_harness.sh` |

Processos em execução (compose de produção, `bhub-backend-python/docker-compose.prod.yml`):

| Serviço | Imagem | Comando | Papel |
|---|---|---|---|
| `backend` | build local `bhub-backend-python-backend:latest` | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*` (`:25-27`) | app web + API; publica só `127.0.0.1:8000` (`:21`) |
| `arq-worker` | a mesma imagem | `arq app.jobs.tasks.WorkerSettings` (`:80`) | executa os jobs |
| `db` | `postgres:16-alpine` (`:117`) | — | banco de produção |
| `redis` | `redis:7-alpine` (`:143`), `--appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru` (`:146`) | — | fila ARQ |

O compose de desenvolvimento (`bhub-backend-python/docker-compose.yml`) declara os mesmos
quatro serviços com defaults mais frouxos: `SECRET_KEY` com default, dependências sem
`condition: service_healthy`, `db` e `redis` sem `healthcheck`, sem `security_opt` e sem
limites de recurso, e sem as variáveis de analytics/consentimento. Mantém
`ENABLE_ARQ=true` (`:17`) e `ENABLE_SCHEDULER=true` no `backend` (`:26`) e
`ENABLE_SCHEDULER=false` no `arq-worker` (`:61`).

---

## 2. Limites dos módulos (CURRENT)

- **Direção das dependências:** `api/` e `web/` dependem de `services/` e de
  `interfaces/`; `services/` dependem de `models/`, `schemas/` e `core/`; `core/` não
  depende de `services/`. Nenhum módulo de `core/` importa `api/`.
- **Injeção de dependência:** os routers recebem serviços por `Depends`, declarados em
  `app/api/deps.py` — sessão (`DBSession`), `ClassifierDep`, `SearchDep`, `AIDep`,
  `FeedAggDep`, `PDFDep`, `OpenGraphDep` (`app/api/deps.py:125-129`). A sessão de banco
  trafega como parâmetro explícito; serviços não abrem sessão própria quando vêm de uma
  rota (`app/api/deps.py:99-108`).
- **Contratos estruturais:** `app/interfaces/services.py` usa `typing.Protocol` +
  `@runtime_checkable`, o que permite substituir implementações por stubs em teste sem
  monkey-patching. `app/interfaces/task_queue.py` define `ITaskQueue` com as duas
  implementações de fila.
- **Fronteira de I/O testável:** `PDFService` recebe `upload_path` e `http_client` no
  construtor (`app/services/pdf_service.py:28`), e `FeedAggregatorService`/`FeedFetcher`
  aceitam `http_client=` — é a costura que deixa as suítes de integração rodarem sem rede.
- **Dívida de tipagem declarada, não escondida:** `mypy app` é bloqueante mas PARCIAL
  (28 de 105 arquivos ficam com `ignore_errors = true` em `pyproject.toml:269-300`); o
  `pyproject.ratchet.toml` roda a mesma config sem esse bloco e o CI falha se o total
  crescer (orçamento 127 / 105 arquivos, `.github/workflows/ci.yml:101-102`).

---

## 3. Banco de dados: desenvolvimento vs produção (CURRENT)

**Produção é PostgreSQL.** A escolha está na ADR-0001 e no código:

- O compose de produção injeta `DATABASE_URL` com default
  `postgresql+asyncpg://bhub:bhub@db:5432/bhub` no `backend` e no `arq-worker`
  (`bhub-backend-python/docker-compose.prod.yml:32` e `:85`).
- `app/database.py:27-33` reconhece o dialeto Postgres e cria o engine com
  `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=3600`.
- `init_db()` cria `CREATE EXTENSION IF NOT EXISTS pg_trgm`, o trigger
  `articles_search_vector_trigger` e a função `articles_search_vector_update()`
  (`app/database.py:109-140`).

**Desenvolvimento e suíte unitária usam SQLite.** O default de `settings.database_url` é
`sqlite+aiosqlite:///./bhub.db` (`app/config.py:59`) e a suíte unitária roda em memória
(`tests/conftest.py:19`). É compatibilidade de desenvolvimento, não o banco de produção:

- `app/database.py:35-40` monta os kwargs do ramo não-Postgres (`StaticPool` para
  `:memory:`, `connect_args` de SQLite).
- `app/database.py:49-57` liga `PRAGMA journal_mode=WAL` / `synchronous=NORMAL` quando a
  URL é SQLite.
- `app/database.py:142-186` cria a tabela virtual `articles_fts` (FTS5) e os triggers
  `articles_ai` / `articles_ad` / `articles_au` **apenas** nesse ramo.
- `app/models/article.py:103-108` declara `search_vector` como
  `TSVECTOR().with_variant(Text(), "sqlite")` — a mesma coluna serve aos dois dialetos.

**Migrações.** A cadeia é aplicada por `alembic upgrade head`; `alembic/env.py:40`
sobrescreve `sqlalchemy.url` com `settings.database_url`, então quem decide o alvo é a
variável de ambiente do processo, não o `alembic.ini`. O caminho `008_postgres_fts` cria a
extensão, a coluna `TSVECTOR`, a função e o trigger de atualização, e os índices
`idx_articles_search_vector` (GIN) e `idx_articles_title_trgm` (`gin_trgm_ops`)
(`alembic/versions/008_postgres_fts.py:29-71`). O `009_feed_http_cache` adiciona
`feeds.http_etag` e `feeds.http_last_modified`.

**O que foi provado com banco real:** `tests/integration/test_migrations.py` roda
`alembic upgrade head` num PostgreSQL 16 vazio, por subprocesso, e inspeciona o catálogo
(tipo da coluna `search_vector` resolvido em `pg_attribute`/`pg_type`, não por string).
`tests/integration/conftest.py` exige containers reais e nunca faz `pytest.skip`.

---

## 4. Worker (CURRENT)

**ARQ sobre Redis é a estratégia de jobs.** É uma decisão registrada na ADR-0002.

- **Configuração central:** `WorkerSettings` em `app/jobs/tasks.py:158-172` —
  `functions = [task_classify_article, task_download_pdf]`, `max_jobs = 10`,
  `job_timeout = 300`, `max_tries = 3`, `retry_jobs = True`, `keep_result = 86_400`,
  `health_check_interval = 30`, `redis_settings` derivado de `settings.redis_url`.
- **Hooks:** `startup` guarda `async_session_maker` no `ctx`, liga telemetria quando
  `enable_telemetry` e inicializa o `EmbeddingClassifier` + embeddings das categorias
  (`app/jobs/tasks.py:89-119`); `on_job_start` cria a sessão e o contexto de observação
  (`:128-135`); `on_job_end` fecha a sessão e registra sucesso/falha (`:138-155`);
  `shutdown` fecha o que sobrou (`:122-125`).
- **Jobs:** `task_classify_article` (`:24-45`) e `task_download_pdf` (`:48-86`), ambos
  decorados por `@observed_job`.
- **Seleção da fila no processo web:** `get_task_queue()`
  (`app/services/task_dispatcher.py:67-79`) devolve `ArqTaskQueue` quando
  `settings.enable_arq` é verdadeiro e `InlineTaskQueue` caso contrário. O pool ARQ é
  criado sob demanda (`:26-38`) e **pré-aquecido no lifespan**; em produção, falha de
  conexão no bootstrap é fatal (`app/main.py:56-70`).
- **Recusa explícita de degradação:** com `ENABLE_ARQ=true` e sem pool, o dispatcher
  levanta `RuntimeError` em vez de executar localmente (`app/services/task_dispatcher.py:82-89`), e
  falha de enfileiramento é logada e propagada (`app/interfaces/task_queue.py:46-59`).
- **`InlineTaskQueue` é fallback de desenvolvimento.** Ele executa o trabalho no event
  loop atual via `asyncio.create_task` (`app/interfaces/task_queue.py:90-93`), rastreia as
  tarefas em `_pending` e `close_task_queue()` aguarda todas antes de encerrar
  (`app/services/task_dispatcher.py:58-64`). A própria docstring do módulo declara que esse é o ÚNICO
  ponto do código onde `create_task` é permitido e que ele só vale com `ENABLE_ARQ=false`
  (`app/interfaces/task_queue.py:72-80`).
- **Ordem de disparo:** o `commit` do banco acontece **antes** do enfileiramento
  (`app/services/feed_aggregator.py:223` e depois `:231`/`:238`). Não há transação
  compartilhada entre banco e Redis — ver KNOWN RISK `R-01`.

**O que foi provado com infraestrutura real:** `tests/integration/test_arq_worker.py`
exercita dispatcher → Redis 7 → worker ARQ de produção (modo `burst`) → PostgreSQL 16,
sem mocks: enqueue, execução, gravação no banco, idempotência sequencial e concorrente,
retenção em `arq:queue`, propagação de retry e falha terminal.

---

## 5. Scheduler (CURRENT)

APScheduler `AsyncIOScheduler` com timezone `America/Sao_Paulo` (`app/jobs/scheduler.py:14`).

- **Um job:** `sync_feeds`, `CronTrigger(minute=0)` — de hora em hora, no minuto zero
  (`app/jobs/scheduler.py:62-68`), apontando para `sync_all_feeds_job` (`:17-41`).
- **Gate de configuração:** não registra nem inicia se `settings.enable_scheduler` for
  falso ou `settings.scheduler_mode == "off"` (`:52-59`, `:75-79`). O default é
  `enable_scheduler = True` e `scheduler_mode = "app"` (`app/config.py:107`, `:111`).
- **Exclusão mútua entre instâncias:** o job roda dentro de `distributed_lock("sync_feeds")`
  (`app/jobs/scheduler.py:23`), um lock de banco com TTL de 30 min e heartbeat de 5 min
  (`app/core/scheduler_lock.py:22-25`). Lock não adquirido gera `RuntimeError`, que o job
  trata como "outra instância está executando" (`app/jobs/scheduler.py:37-39`).
- **Quem roda o scheduler:** no compose, só o `backend` (`ENABLE_SCHEDULER=true`,
  `docker-compose.prod.yml:43`); o `arq-worker` recebe `ENABLE_SCHEDULER=false` (`:94`).
- **Status:** `get_scheduler_status()` devolve `{running, jobs[]}`
  (`app/jobs/scheduler.py:93-108`).

---

## 6. Busca (CURRENT)

`SearchService` (`app/services/search_service.py`) escolhe o motor pelo dialeto da sessão.

- **PostgreSQL (produção):** `search()` detecta o dialeto (`:22-24`) e chama
  `_search_postgres_ids` (`:56-80`), que usa `plainto_tsquery('portuguese', ...)` e ordena
  por `ts_rank_cd(Article.search_vector, ts_query)` com desempate por
  `publication_date DESC`; o filtro de casamento usa o operador `@@` sobre `search_vector`.
- **SQLite (dev/testes):** cai em `search_fts5` e, se não houver resultado, em
  `search_like_fallback` (`:36-40`).
- **Índices e trigger:** criados pela migração `008_postgres_fts` e repetidos no
  `init_db()` (`app/database.py:114-140`). A coluna recebe pesos: `title` como `A` e
  `abstract` como `B`, em português **e** em inglês.
- **Sugestões:** `suggest()` / `get_suggestions()` (`:45-47`), com caminho de similaridade
  (`pg_trgm`) no PostgreSQL (`:251-260`).
- **Sanitização:** `_sanitize_plain_query` prepara o texto para `plainto_tsquery`
  (`:356`), e o serviço reporta o motor em uso como `postgresql_tsvector` ou
  `sqlite_fts5` (`:399-421`).

**O que foi provado com banco real:** `tests/integration/test_postgres_search.py` cobre
os cinco cenários do plano (português, inglês, ranking, busca inexistente, sugestão) e os
caminhos de falha (não publicado fora da busca, query vazia/pontuação, SQL que não é
executado).

---

## 7. IA (CURRENT)

- **Facade:** `AIManager` (`app/ai/manager.py`). Ordem de provedores para classificação:
  **DeepSeek → LLM local → OpenRouter → HuggingFace** (`:71-77`); para tradução o mesmo
  arranjo sem o HuggingFace (`:114-117`). Um provedor só entra no dicionário se a chave
  correspondente estiver configurada (`:41-62`).
- **Fallback instrumentado:** cada queda de provedor chama `record_ai_fallback`
  (`app/ai/manager.py:98-100`), que alimenta a métrica `ai.fallback.total` quando o
  OpenTelemetry está ativo (`app/core/telemetry.py:22-35`).
- **ML local:** `EmbeddingClassifier` com `paraphrase-multilingual-MiniLM-L12-v2`
  (`app/config.py:129-130`), inicializado no lifespan do app (`app/main.py:72-83`) e
  também no startup do worker (`app/jobs/tasks.py:111-119`). Sem o modelo, cai em
  `HeuristicClassifier`.
- **Rotas:** `POST /api/v1/ai/classify`, `POST /api/v1/ai/translate`,
  `GET /api/v1/ai/status` (`app/api/v1/ai.py:57`, `:105`, `:203`).
- **Tradução com cache:** `TranslationCacheService` + modelo `TranslationCache`
  (`app/services/translation_cache_service.py`, `app/models/translation_cache.py`), com
  chave derivada de texto + idiomas (`app/api/v1/ai.py:21-25`).
- **LLM local opcional:** `app/ai/local_llm_service.py`, habilitado por
  `LOCAL_LLM_ENABLED` (`app/config.py:133-140`); o import é condicional
  (`app/ai/__init__.py:16-19`).

---

## 8. Ingestão (CURRENT)

Fluxo vigiado ponta a ponta por `tests/integration/test_feed_pipeline.py`:

```
APScheduler (sync_feeds, de hora em hora)
  └─► FeedAggregatorService.sync_all_active_feeds()
        └─► por feed: FeedFetcher (conditional GET com ETag/Last-Modified)
              └─► ArticleParserService.parse_entry()  (título, DOI, abstract, autores,
                                                        is_open_access, pdf_url)
                    └─► deduplicação
                          └─► persistência (Article + autores)
                                └─► await self.db.commit()          ← feed_aggregator.py:223
                                      └─► dispatch_classify_article()  ← :231
                                      └─► dispatch_download_pdf()      ← :238 (só OA com pdf_url)
```

- **Quem enfileira hoje:** o único produtor é `sync_feed`
  (`app/services/feed_aggregator.py:231`, `:238`). O dispatcher expõe as fachadas
  `dispatch_classify_article` / `dispatch_download_pdf`
  (`app/services/task_dispatcher.py:92-105`) para preservar as assinaturas públicas — não
  há rota de API enfileirando job.
- **PDF:** `PDFService.process_article_pdf` baixa, valida magic bytes, extrai metadados e
  texto (PyMuPDF/pdfplumber), grava em `uploads/pdfs`, calcula `sha256` e persiste a
  linha de `pdf_metadata` numa operação transacional com `commit`/`rollback` controlados
  (`app/services/pdf_service.py:383-494`).
- **Scraping e Open Graph:** `app/services/web_scraper.py` e `app/services/opengraph_service.py`,
  injetados por `Depends` (`app/api/deps.py:99-108`).
- **Cache HTTP dos feeds:** `feeds.http_etag` / `feeds.http_last_modified` são atualizados
  a cada sync bem-sucedido (`app/services/feed_aggregator.py:211-213`) — colunas criadas na
  migração `009_feed_http_cache`.
- **O que foi provado, caso a caso:** artigo persistido; autores associados; job disparado
  **somente depois do commit** (a sonda do teste lê por conexão independente, não por texto
  do serviço); duplicata não cria artigo novo; entrada inválida não aborta o feed.

---

## 9. Observabilidade (CURRENT)

- **Logs:** Loguru com sinks e rotação configurados em `app/core/logging.py`
  (`LOG_ROTATION=10 MB`, `LOG_RETENTION=1 month`, `LOG_JSON` opcional —
  `app/config.py:147-150`). Existe `app/core/log_sanitizer.py` para o que vai a log/webhook.
- **Alertas:** sink opcional de webhook por nível mínimo, best-effort e sanitizado
  (`app/core/alerting.py:16-37`; `ALERT_WEBHOOK_URL` / `ALERT_MIN_LEVEL`,
  `app/config.py:153-155`).
- **OpenTelemetry (opt-in):** `ENABLE_TELEMETRY=false` por default
  (`app/config.py:158`). Quando ligado, `setup_telemetry` cria provider de traces com
  exportador OTLP gRPC e métricas `ai.classify.duration_ms`, `ai.fallback.total`,
  `feed.ingested.total`, `feed.failed.total` (`app/core/telemetry.py:13-40`).
- **Telemetria de jobs:** `app/jobs/observe.py` emite log estruturado por job
  (`job_type, job_id, article_id, attempt, status, duration, exception`) e, quando o
  tracer está ativo, contadores `arq.job.success` / `arq.job.failure`, histograma
  `arq.job.duration` e span `arq.job` (`app/jobs/observe.py:40-66`, `:106-164`). A
  telemetria nunca derruba o job (`:142-143`).
- **Health:** `GET /health` devolve versão, `database`, `ml_model` e timestamp
  (`app/main.py:348-361`). O Dockerfile usa `curl -f http://localhost:8000/health`
  (`Dockerfile:64-65`) e o `arq-worker` desliga o healthcheck porque não tem HTTP
  (`docker-compose.prod.yml:100-102`).
- **Analytics:** middleware registrado sempre, com gate avaliado por request
  (`app/main.py:152-155`; `app/core/analytics_middleware.py`), respeitando consentimento
  e DNT (`app/config.py:161-167`).
- **Rate limiting:** slowapi, `Limiter(key_func=get_remote_address)`
  (`app/core/limiter.py:10`), handler registrado em `app/main.py:132-134`. Ver KNOWN RISK
  `R-05` sobre um dos endpoints.

---

## 10. Deploy (CURRENT)

- **Stack:** `docker compose -f docker-compose.prod.yml up -d` **de dentro de
  `bhub-backend-python/`** (é o único compose com PostgreSQL; ver `docs/deploy/RUNBOOK.md`).
- **Topologia:** Traefik na frente (TLS + domínio), app publicado apenas em
  `127.0.0.1:8000` (`docker-compose.prod.yml:18-21`), `--proxy-headers
  --forwarded-allow-ips=*` para o esquema/IP reais chegarem ao app (`:22-27`).
- **Containers:** `python:3.12-slim`, usuário não-root `appuser` (`Dockerfile:56-58`),
  modelo de embeddings pré-baixado na imagem (`Dockerfile:42-47`), torch CPU
  (`Dockerfile:32`).
- **Volumes:** `./uploads:/app/uploads` e `./logs:/app/logs` (`:28-30`); volumes nomeados
  `postgres_data` e `redis_data` (`:164-166`).
- **Liveness/limites:** healthchecks com `condition: service_healthy` para `db` e `redis`
  (`:50-54`, `:126-131`, `:149-153`), healthcheck do backend com `start_period: 60s`
  (`:55-60`), `no-new-privileges` e tetos de CPU/memória por serviço (`:61-69`,
  `:103-109`, `:132-135`, `:154-157`), rotação de log `10m × 3` (`:70-74`).
- **Segredos:** `SECRET_KEY` e `POSTGRES_PASSWORD` são obrigatórios via `.env`
  (`docker-compose.prod.yml:35`, `:88`, `:123`). `SECRET_KEY` tem validação própria em
  produção (`app/config.py:71-89`) e `ALLOWED_ORIGINS` recusa wildcard em produção
  (`app/config.py:45-55`).
- **Migrações:** `alembic upgrade head` (passo do procedimento de deploy;
  `docs/deploy/RUNBOOK.md` documenta o caso do banco que já tem tabelas sem
  `alembic_version`).
- **Upload para a VPS:** `upload-to-vps.sh` (raiz) → `/var/www/bhub/backend/`; scripts
  operacionais em `bhub-backend-python/scripts/vps/`.
- **CI:** `.github/workflows/ci.yml` (raiz), `working-directory: bhub-backend-python`,
  Python 3.12. Steps: `ruff check app tests` (`:39-40`), `ruff format --check .` (`:42-43`),
  `mypy app` (`:55-56`), ratchet de mypy fail-closed com orçamento 127 / 105 arquivos
  (`:88-102`), harness do step do ratchet (`:235-236`), `pytest tests/ -v` (`:238-239`),
  piso de cobertura `--cov-fail-under=59.19` com precisão 2 (`:274-281`), integração real
  `pytest tests/integration -m integration -v` (`:306-314`) e build da imagem Docker
  (`:348-350`).

---

## 11. PLANNED

Nada nesta seção existe. É backlog declarado, sem implementação.

- **Busca vetorial/semântica real** (embeddings de artigo + similaridade): não existe. O
  filtro `search_type=semantic` da UI web é uma **aproximação** — classifica a consulta com
  o `EmbeddingClassifier`, usa a categoria resultante como filtro e roda busca textual
  (`app/web/routes.py:38`, `:90-116`) —, e a seção de busca do ADR-0003 registra isso como
  "preparado para o futuro".
- Dashboards/métricas além do que existe: hoje há logs estruturados, webhook de alerta
  opcional e métricas OTel quando ligadas; painel/alertas avançados não existem.
- Documentação pública da API (`docs_url`/`redoc_url` só aparecem com `DEBUG=true` —
  `app/main.py:127-128`).
- `ROADMAP.md`: a estrutura proposta pelo plano prevê `docs/architecture/ROADMAP.md`; o
  arquivo **não existe** no repositório. O plano vigente
  (`docs/superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md`) faz esse papel.

## 12. DEFERRED

Reconhecido, decidido adiar de propósito, com registro. A correção exige uma task própria.

| Item | O que falta | Registro |
|---|---|---|
| M5 (Task 11) | O CI faz build da imagem mas **não** executa `docker run … python -c "import app.main"`, então não prova que a imagem é utilizável | `.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/task-11-report.md:271`, `:295` |
| Cenários 25, 29 e 31 do harness do ratchet | Nos três casos de tabela inline só a asserção do guard se reproduz (a config injetada duplica `[tool.mypy]`) | `docs/quality/BASELINE.md:674` |
| `.dockerignore` | Não existe em `bhub-backend-python/`; o contexto de build inclui tudo | `docs/quality/BASELINE.md:265` |

## 13. KNOWN RISKS

Existem hoje. **Registrados, não corrigidos** — nenhum item desta seção foi alterado por
este documento.

**R-01 — Não existe outbox entre o commit e o despacho do job.** O `commit` do banco
precede o enfileiramento no Redis (`app/services/feed_aggregator.py:223`, `:231`, `:238`)
e **não há transação compartilhada entre banco e fila**. Se o processo morrer nessa
janela, o artigo fica persistido e o job de classificação/PDF se perde sem retry. A ordem
está correta e é o que os testes prendem; a **atomicidade não existe**.
`tests/integration/test_feed_pipeline.py` declara o risco explicitamente na docstring.

**R-02 — T16-F1: TOCTOU na deduplicação de PDF por hash.** Dois jobs com os MESMOS bytes
passam ambos por `check_duplicate` (`app/services/pdf_service.py:454` +
`:338-345`) antes de qualquer `commit` (`:489`); o perdedor morre em
`pdf_metadata_file_hash_key` com `jobs_failed=1` e `retried=0` — falha **terminal**, sem
retry — e o artigo perdedor pode terminar **sem PDF**. Medição da Task 16: **5/5**
tentativas concorrentes, vencedor não-determinístico, 0 órfãos em disco. A única garantia
de unicidade hoje é a constraint do banco, não a pré-checagem.
Registro: `.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/task-16-review.md:191`,
`tests/integration/test_pdf_pipeline.py:68-76`.

**R-03 — RED-3: `max_tries`/`retry_jobs` são configuração morta para os jobs do repositório.**
`WorkerSettings` declara `max_tries = 3` e `retry_jobs = True`
(`app/jobs/tasks.py:168-169`), mas o ARQ só re-tenta exceções do tipo
`Retry`/`RetryJob`/`CancelledError` e nenhum código em `app/` as levanta. Na prática, uma
exceção comum morre no `job_try=1` (medido na Task 14). Retry **existe como mecanismo** e
foi provado com uma função local ao teste; **não** vale para os dois jobs do repo.

**R-04 — RED-5: o startup do worker custa ~12 s e toca a rede.** `startup()` carrega
`paraphrase-multilingual-MiniLM-L12-v2` e os embeddings das categorias a cada subida do
worker — 11,5–13,5 s medidos — e faz uma requisição ao HF Hub
(`app/jobs/tasks.py:111-119`). Sem embeddings, a classificação degrada silenciosamente
para a heurística.

**R-05 — Rate limiting do `POST /api/v1/ai/translate`.** Os decorators `@limiter.limit`
estão presentes (`app/api/v1/ai.py:106-107`), mas o parâmetro que o slowapi procura chama-se
`request` e, nesse endpoint, `request` é o **corpo Pydantic** (`TranslateRequest`); o
`starlette.requests.Request` está em `_http_request` (`:112`), que ninguém consome. A
chave/limite não opera como pretendido nessa rota. (`/classify` não tem esse problema —
`app/api/v1/ai.py:58-62`.)

**R-06 — `get_or_create_category` é check-then-act.** `SELECT` por `Category.slug` (linha
141) seguido de `db.add()` + `db.flush()` (linhas 160-161), sem `ON CONFLICT`
(`app/services/classification_service.py:118-161`). Dois jobs que criem a MESMA categoria
nova ao mesmo tempo colidem na unicidade de `categories.slug`. É a mesma forma do defeito
corrigido no vínculo artigo↔categoria (RED-1, fix do commit `f48577a`), agora em outra
tabela.

**R-07 — O ratchet de mypy tem um limite inerente no desenho por contagem.** O guard do CI
inspeciona a config com `sed` / `grep` e cobre a chave `ignore_errors`; outra relaxação
(`disable_error_code`, `follow_imports`) reduz o total sem ser detectada
(`docs/quality/BASELINE.md` §6.8; `.github/workflows/ci.yml:135-139`). O conserto
estrutural (ler a config com `tomllib`) é follow-up declarado, não feito.

**R-08 — N1 (Task 13): a capacidade de falhar do teste de ordenação depende do plano do
PostgreSQL.** Com `enable_sort=off` (HashAggregate) a query sem `ORDER BY` devolve a ordem
esperada e o teste passa por acidente. No plano default o mutante é pego.
`.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/task-13-rereview.md:32`, `:251`.

**R-09 — `skipped` do pipeline de PDF é ambíguo.** O mesmo status cobre "não havia
trabalho" (já tem PDF, não é OA, sem URL, duplicata por hash) e "o trabalho falhou"
(404/500/timeout/payload inválido), então um alerta sobre `skipped` não é sinal de saúde.
`tests/integration/test_pdf_pipeline.py:56-63`.

**R-10 — Templates ainda anunciam SQLite como banco.** A página "Sobre" dos templates
renderizados (`app/templates/pages/about.html:172`, e a cópia em
`design-review/frontend/templates/pages/about.html:172`) diz ao visitante que o banco é
"SQLite otimizado com FTS5". É copy de produção, não documentação; fora do escopo desta
task (é `app/`).

**R-11 — O backup automático não cobre o PostgreSQL.** `scripts/vps/backup.sh` copia um
**arquivo** (`bhub.db`, `:40-49`) para `/var/backups/bhub` e, se o arquivo não existir,
apenas emite warning — num deploy com PostgreSQL ele não falha, mas também não salva nada
do banco de produção. O mesmo vale para `scripts/backup_db.py` / `scripts/restore_db.py`,
que usam `import sqlite3`. O caminho correto é `pg_dump` contra o serviço `db`
(documentado em `docs/deploy/RUNBOOK.md`). **Registrado, não corrigido** (exige tocar
`scripts/`).

**R-12 — O modo `semantic` da busca usa um motor que só existe em desenvolvimento.**
`app/web/routes.py:110` chama `search_service.search_fts5(...)`, e a tabela virtual FTS5 é
criada **apenas** no ramo SQLite (`app/database.py:142-186`). Num deploy PostgreSQL a
chamada levanta e o `except` de `:117-118` a converte em `log.warning`, seguindo para a
busca textual com o filtro de categoria já aplicado (`:106-108`) — ou seja, o modo
"semântico" degrada para busca textual. **Observação de leitura de código; não medida
contra PostgreSQL nesta rodada.** Registrada, não corrigida.

## 14. HISTORICAL

Documentos que descrevem uma arquitetura ANTERIOR. Não são a arquitetura atual.
A marcação sistemática (T5.3) é da Task 18; o que já foi corrigido nesta rodada está
indicado na tabela.

| Documento | Estado |
|---|---|
| `bhub-backend-python/ARCHITECTURE_REPORT.md` | **HISTÓRICO marcado** (análise de 06/mai/2026), com notas de CORREÇÃO em §1 (infra), §4.1, §7 e §9. Afirmava `asyncio.create_task` como estratégia de jobs e SQLite como infraestrutura — nenhum dos dois é verdade hoje. |
| `BHUB_REFACTORING_PLAN.md` (raiz) | **HISTÓRICO marcado** (plano de refatoração). Seus itens não marcados já foram executados (ARQ, DI, migração para PostgreSQL). Não é backlog aberto. |
| `docs/ESTADO_ATUAL_PROJETO.md` | **HISTÓRICO marcado** (análise de dez/2024). As afirmações de produção foram corrigidas: banco = PostgreSQL 16, busca = `TSVECTOR` + `pg_trgm`. |
| `docs/deploy/SQLITE_LIMITS.md` | **HISTÓRICO marcado** nesta rodada. Era o documento que afirmava SQLite em produção. |
| `docs/deploy/DEPLOY_PROD.md` | **HISTÓRICO marcado** nesta rodada (checklist da era SQLite). |
| `bhub-backend-python/agents.md` | Descreve IA/ML de uma revisão antiga ("Future Improvements" já atendidas por `app/core/telemetry.py`). Ainda não marcado — Task 18. |
| `docs/arquitetura/*` (`MIGRATION_GUIDE.md`, `MIGRATION_GUIDE_BACKEND.md`, `bhub-stack-recomendada.md`, `bhub-design-reference.md`) | Guias da migração Next.js → Python; dois ainda listam SQLite (`MIGRATION_GUIDE.md:14`, `MIGRATION_GUIDE_BACKEND.md:14`). Ainda não marcados — Task 18. |
| `docs/deploy/MAPA_EXECUCAO_DEPLOY.md`, `CHECKLIST_GO_NOGO.md`, `DEPLOY_STAGING.md`, `RESUMO_IMPLEMENTACAO.md`, `VPS_DEPLOY.md` | Documentos operacionais da era SQLite. Ainda não marcados — Task 18. |
| `docs/configuracao/DOCUMENTACAO_BACKEND.md` | Documentação de backend anterior à migração para PostgreSQL (`:35`, `:211`, `:296`, `:654`). Ainda não marcado — Task 18. |
| `README.md` (raiz) | Ainda lista "SQLite com FTS5" na stack (`:10`) e o default SQLite em `:171`. Ainda não marcado — Task 18. |

**Referências cruzadas que continuam válidas:** `docs/quality/BASELINE.md` (baseline de
qualidade e limites declarados dos gates), `docs/superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md`
(plano vigente) e `CLAUDE.md` (orientação operacional — já aponta para cá; o rewiring
completo de `CLAUDE.md`/`AGENTS.md` é da Task 18).

---

**Última verificação deste documento:** leitura final contra o código no baseline
`399915d`, após a última edição da Task 17.
