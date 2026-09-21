# BHub v1.1 — Checklist de Release (verificação de código)

> **Status deste documento:** verificação de código e testes dos itens do checklist de release.
> É o deliverable literal da **Task 19** (Épico 6) do
> [`plano v1.1`](../superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md).
>
> **Baseline:** HEAD `9091bc8`, árvore limpa, worktree `feat/v1.1-reliability`.
> **Data da verificação:** 19/09/2026.
> **Autoridade da arquitetura:** [`CURRENT_ARCHITECTURE.md`](../architecture/CURRENT_ARCHITECTURE.md)
> — se algo aqui divergir do código, **o código está certo**.

---

## 1. Método (e o que este documento NÃO é)

Cada item recebe um status e a evidência que o sustenta. As evidências têm dois níveis, sempre
rotulados:

| Rótulo | Significado |
|---|---|
| **[MEDIDO]** | Comando executado nesta verificação, com `rc` real e saída observável. |
| **[LIDO]** | Leitura de código/config/teste com `arquivo:linha` conferido no disco. Não é execução. |
| **[NÃO VERIFICADO]** | Não foi executado, e não se afirma que passou. O motivo é declarado. |

**O que este documento não é:** não é prova de que a release foi liberada. As seções **§9 (Staging)**,
**§5.6 (build da imagem)** e **§10 (GitHub Actions)** descrevem verificações que **exigem uma
execução externa a esta máquina** e que **não** foram feitas. Elas estão marcadas como tal — não
como aprovadas por omissão.

### 1.1 Bateria de gates (medida nesta verificação)

| Gate | Comando | Resultado | rc |
|---|---|---|---|
| `git diff --check` | (raiz do worktree) | sem saída | **0** |
| Ruff | `ruff check app tests` | `All checks passed!` | **0** |
| Formatter | `ruff format --check .` | `190 files already formatted` | **0** |
| Mypy | `mypy app` | `Success: no issues found in 105 source files` | **0** |
| Ratchet | `mypy app --config-file pyproject.ratchet.toml` | `Found 127 errors in 28 files (checked 105 source files)` | **1** (esperado) |
| Unit | `pytest tests/ -q` | `270 passed, 48 deselected` | **0** |
| Integração | `pytest tests/integration -m integration -q` (idêntico ao CI) | `48 passed` — **ver a ressalva de disco em §1.2** | **0** |
| Cobertura | `pytest tests/ -q --cov=app --cov-precision=2 --cov-fail-under=59.19` | `TOTAL 6345 2563 59.61%` · `Required test coverage of 59.19% reached.` | **0** |
| Harness do ratchet | `RATCHET_HARNESS_COVERAGE=1 bash tests/ci/ratchet_step_harness.sh` | `35 disponíveis, 35 executados, 35 ok, 0 divergências, 0 pulados` | **0** |

Os valores acima são do **HEAD atual** (pós-F1). A bateria foi medida duas vezes: em `9091bc8`+verificação
e novamente após o fix — os números de então estão preservados em §1.3, porque foram a base do
veredito de verificação.

**Delta contra o baseline congelado (explicado, não silenciado).** O baseline autoritativo da
milestone é `258 passed / 48 deselected`, cobertura `6343 2586 59.23%` e `188 files`. O verificado
aqui é `270 passed`, `6345 2563 59.61%` e `190 files`. As causas são **duas**, ambas desta task: o
arquivo de teste que fechou o item **8.4** (`tests/unit/test_article_parser_ojs_authors.py`, 6 testes)
e — já na rodada de fechamento — o teste que guarda o F1
(`tests/unit/test_config_production_arq.py`, 6 testes) junto das **10 linhas** do guard em
`app/config.py`. Os `+12` testes explicam `264→270`; os statements cobertos subiram com os testes e
caíram com o guard novo (`6343→6345` statements, `2573→2563` não cobertos). A atribuição do delta
de verificação foi confirmada por revisor independente comparando baseline e HEAD **menos** o arquivo
novo: idênticos arquivo a arquivo (105 arquivos, 6343 statements, 2586 missing).

**Nenhum gate foi relaxado:** o orçamento do ratchet segue **127**, o piso de cobertura segue
**`--cov-precision=2 --cov-fail-under=59.19`**, `strict = true` segue global, o `addopts` de
deseleção não foi tocado e há **0** chaves `continue-on-error` no workflow.

**`app/`:** a verificação em si não alterou nenhuma linha de `app/`. O fix autorizado do F1 alterou
**10 linhas em um arquivo** — `git diff --stat 95cb1d1..HEAD -- bhub-backend-python/app/` devolve
`app/config.py | 10 ++++++++++`, não vazio (a frase anterior, que dizia ser vazio, valia para
`9091bc8..95cb1d1` e ficou obsoleta com o fix).

### 1.2 Ambiente observado

- Docker Engine **29.8.0**; imagens `postgres:16-alpine` e `redis:7-alpine` já locais (a suíte de
  integração falha alto se faltarem — nunca `skip` silencioso).
- **Disco do VM do Docker: `98%`, `1.1G` livres no fim da rodada de fechamento** (era `94%` / `3.1G`
  livres na verificação). O `48 passed` da integração foi medido **antes** do esgotamento; depois
  dele, a suíte **não é reproduzível** por falta de espaço (`No space left on device`, `DiskFullError`).
  O revisor independente não pôde reproduzir os 48 — registrado como limitação de ambiente, que
  **não refuta** a medição anterior e **não** foi causada pelo fix (ver §5.6). **Nenhuma limpeza foi
  executada** em nenhuma rodada (nenhum `prune`, em nenhuma forma): não há autorização permanente.
- `unset DEBUG` aplicado em toda execução de `pytest`/`alembic` (o `DEBUG=release` ambiente quebra
  `app/config.py` com `ValidationError`).

### 1.3 Bateria da verificação (histórico, preservado)

Medida antes do fix do F1, sobre `9091bc8`+os três commits de verificação. Preservada porque foi a
base do veredito de verificação e porque é contra ela que o §1.1 mostra o delta do fix:

```text
Unit         264 passed, 48 deselected
Cobertura    TOTAL 6343 2573 59.44%   (piso 59.19)
Formatter    189 files
Integração   48 passed
```

O `app/` era então **0 linhas** (`git diff --stat 9091bc8..95cb1d1 -- bhub-backend-python/app/` vazio).
O fix do F1 somou 10 linhas em `app/config.py` e 6 testes, como descrito em §1.1 e §15.

---

## 2. Código (plano:1353–1359)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 2.1 | Nenhuma task crítica usa `asyncio.create_task()` em produção | **PASS (com ressalva medida)** | **[LIDO]** `grep -rn create_task app/` → apenas 2 hits reais: `app/interfaces/task_queue.py:77` (docstring) e `:91` (corpo de `InlineTaskQueue._run_inline`). A seleção da fila é `app/services/task_dispatcher.py:73-79`: `enable_arq=True` → `ArqTaskQueue`; `False` → `InlineTaskQueue`. **[MEDIDO]** a produção documentada fixa ARQ ligado: `docker-compose.prod.yml:34` (`ENABLE_ARQ=${ENABLE_ARQ:-true}`) e `:87` do serviço `arq-worker` (`ENABLE_ARQ=true`). **Ressalva resolvida:** com `ENVIRONMENT=production ENABLE_ARQ=false` o processo **aceitava** a configuração e `get_task_queue()` devolvia `InlineTaskQueue`; a combinação passou a ser **rejeitada no startup** (§11-F1, §15). |
| 2.2 | Jobs ARQ são idempotentes | **PASS** | **[MEDIDO]** `tests/integration/test_arq_worker.py` 8 passed: reexecução sequencial (`:339`) e **dois dispatches concorrentes** (`:382`) com worker ARQ + Redis + PostgreSQL reais. **[MEDIDO]** o caso concorrente é uma regressão real: o defeito era `IntegrityError uq_article_category` com `jobs_failed=1` (Task 14), corrigido por `INSERT … ON CONFLICT (article_id, category_id) DO NOTHING` dialeto-aware (`app/services/classification_service.py`), com prova de mutação nos dois sentidos. Cobertura unitária adicional: `tests/unit/test_arq_job_idempotency.py` (5) e `tests/unit/test_classification_concurrent_link.py` (2). |
| 2.3 | PDF job não depende de `background_tasks.py` | **PASS** | **[LIDO]** `grep -n background_tasks app/jobs/tasks.py` → **0 hits**. `task_download_pdf` (`app/jobs/tasks.py:48-86`) opera via `PDFService.process_article_pdf`. **[MEDIDO]** `tests/integration/test_pdf_pipeline.py` 11 passed com worker ARQ real. O único import de `background_tasks` vivo é `app/interfaces/task_queue.py:101`, dentro do executor inline de desenvolvimento. |
| 2.4 | Dependências externas dos serviços críticos são substituíveis | **PASS** | **[MEDIDO]** `tests/unit/test_dependencies.py` 14 passed; `tests/unit/test_feed_aggregator_dependencies.py` 4 passed. **[LIDO]** costuras: `PDFService(upload_path, http_client)`, `OpenGraphService(db)`, `FeedAggregatorService(db, ai_manager, parser, fetcher, http_client)` (`app/services/feed_aggregator.py:38-45`). Fronteira HTTP é o **único** dublê autorizado pelo plano, e é o usado. |
| 2.5 | Não existem singletons mutáveis sem justificativa | **PASS** | **[LIDO]** `docs/architecture/GLOBAL_SINGLETONS.md` (Task 8) documenta as 11 globais com decisão (MANTER/remover) e razão; `get_classifier()` morto foi removido. |

---

## 3. Banco (plano:1363–1370)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 3.1 | PostgreSQL é o banco de produção | **PASS** | **[MEDIDO]** `bhub-backend-python/docker-compose.prod.yml:32` → `DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://bhub:bhub@db:5432/bhub}`. **[LIDO]** ADR-0001 (`docs/adr/0001-postgresql-producao.md`). O compose da **raiz** fixa SQLite em `:31` e referencia um `./Frontend` inexistente (`:86`) — está **documentado como fora do caminho de deploy** (§11-F7, `README_DOCKER.md:8`); o arquivo em si **não** tem banner de legado. |
| 3.2 | `alembic upgrade head` funciona em banco vazio | **PASS** | **[MEDIDO]** a fixture `migrated_database` (`tests/integration/conftest.py:283-295`) roda `alembic upgrade head` em **banco vazio** via subprocesso, exatamente como o deploy, e **assere `rc=0`**. `tests/integration/test_migrations.py` 9 passed. Isto não era verdade antes da Task 12 (faltava a migração baseline pré-001) — o defeito foi encontrado e corrigido lá. |
| 3.3 | Migrações existentes são reversíveis quando aplicável | **PASS** | **[MEDIDO]** as **10** migrações de `bhub-backend-python/alembic/versions/` declaram `def downgrade` (`000_baseline_pre_001_schema` … `009_feed_http_cache`). **[MEDIDO]** `test_downgrade_base_then_upgrade_head_rebuilds_the_chain` (`test_migrations.py:124`) reconstrói a cadeia inteira `downgrade base` → `upgrade head`. |
| 3.4 | `search_vector` é atualizado corretamente | **PASS** | **[MEDIDO]** `test_search_vector_is_populated_by_the_insert_trigger` (`test_postgres_search.py:236`) — o trigger da 008 popula o vetor sozinho; `test_search_vector_trigger_exists_on_articles` (`test_migrations.py:96`) confere `articles_search_vector_trigger` no catálogo. |
| 3.5 | Índices GIN/pg_trgm existem | **PASS** | **[MEDIDO]** `test_expected_indexes_exist_with_right_method` (`test_migrations.py:78`) assere `idx_articles_search_vector` e `idx_articles_title_trgm` presentes **e** com `USING gin`, lidos de `pg_indexes`; `test_pg_trgm_extension_is_present` (`:69`). |
| 3.6 | Pool SQLAlchemy está configurado **e testado** | **PARCIAL — configurado, NÃO testado** | **[LIDO]** configurado para PostgreSQL: `app/database.py:28-33` → `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=3600`. **[MEDIDO]** `grep -rn "pool_size\|pool_pre_ping\|pool_recycle" tests/` → **0 hits**: nenhum teste assere a configuração do pool. As fixtures de integração usam `NullPool` **de propósito** (`tests/integration/conftest.py:305`, isolamento entre loops), logo o pool de produção não é exercitado por teste algum. A metade "testado" do item **não está satisfeita**. |

---

## 4. Redis / ARQ (plano:1374–1381)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 4.1 | Redis sobe em staging | **NÃO VERIFICADO** | **[NÃO VERIFICADO]** não existe ambiente de staging neste repositório — apenas o guia `docs/deploy/DEPLOY_STAGING.md`. Nenhuma execução de staging foi feita (§9). |
| 4.2 | Worker ARQ sobe em staging | **NÃO VERIFICADO** | **[NÃO VERIFICADO]** idem 4.1. O que **está** provado é que o worker sobe em ambiente controlado real: `tests/integration/test_arq_worker.py` executa `arq.worker.Worker` de produção em `burst=True` contra Redis 7 e PostgreSQL 16 reais. É infraestrutura real, mas **não é o ambiente de staging**. |
| 4.3 | Retry funciona | **PASS (para o mecanismo) / NÃO se aplica aos jobs do repo** | **[MEDIDO]** `test_retry_do_arq_reenfileira_o_mesmo_job_e_vence_no_try_2` (`test_arq_worker.py:502`): `jobs_retried=1`, tentativas observadas `[1, 2]`, `success=True` em `job_try=2` — com função e `WorkerSettings` **locais ao teste**, porque o repositório não tem job re-tentável. **[LIDO]** `WorkerSettings.max_tries = 3` / `retry_jobs = True` (`app/jobs/tasks.py:168-169`) são **configuração morta** para os dois jobs do repo: o ARQ só re-tenta `Retry`/`RetryJob`/`CancelledError` e nada em `app/` as levanta. Está registrado como **R-03** em `CURRENT_ARCHITECTURE.md` §13 — **não** é defeito novo desta verificação. |
| 4.4 | Falha terminal é observável | **PASS** | **[MEDIDO]** `test_excecao_comum_no_job_real_de_producao_termina_no_try_1` (`test_arq_worker.py:575`): o job **real** de produção falha com erro real do PostgreSQL → `jobs_failed=1`, `jobs_retried=0`, `job_try=1`, sem chave de retry no Redis. **[MEDIDO]** a observabilidade da falha: `tests/unit/test_arq_job_observability.py` 19 passed cobrindo log `ERROR` com `exception` e o contador `arq.job.failure` (`app/jobs/observe.py:176`, `:123`). |
| 4.5 | Restart do worker não perde job persistido | **PARCIAL — persistência provada; restart do worker nunca exercitado** | **[MEDIDO]** a persistência do job **antes** de qualquer worker consumir é provada: `test_dispatch_enfileira_job_real_no_redis` (`test_arq_worker.py:238`) assere a chave `arq:job:<job_id>` e o membro no zset `arq:queue` no Redis real. **[MEDIDO]** `grep -rn "restart\|kill\|terminate" tests/integration/` → **0 testes** que derrubem e subam o worker no meio de um job. Não existe teste de restart: o item **não** está provado literalmente, embora a persistência (o mecanismo que o sustenta) esteja. |
| 4.6 | Queue backlog pode ser monitorado | **PARCIAL — inspecionável fora do app; sem superfície no app** | **[MEDIDO]** `grep -rn "queue_depth\|backlog\|zcard" app/` → **0 hits**: não há endpoint, métrica nem comando em `app/` que exponha o tamanho da fila. **[LIDO]** o backlog **é** observável de fora, porque o job vive no zset `arq:queue` (`redis-cli zcard arq:queue`) — é o que a própria suíte de integração faz para se proteger de estado vazado (`test_pdf_pipeline.py:250`, `test_feed_pipeline.py:587`). Um operador consegue monitorar; a aplicação não oferece essa superfície. |

---

## 5. Qualidade (plano:1385–1392)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 5.1 | `ruff check` passa | **PASS** | **[MEDIDO]** `ruff check app tests` → `All checks passed!`, rc=0. Step bloqueante `Lint (ruff check)` (`ci.yml:39-40`), sem `continue-on-error`. |
| 5.2 | `ruff format --check` passa | **PASS** | **[MEDIDO]** `ruff format --check .` → `189 files already formatted`, rc=0 (188 no baseline + o arquivo de teste desta task). Step bloqueante (`ci.yml:42-43`). Versão pinada (`ruff==0.16.7`) para o veredito ser determinístico. |
| 5.3 | `mypy app` passa — **sob o gate PARCIAL de `BASELINE.md` §6.6** | **PASS (literalmente qualificado)** | **[MEDIDO]** `mypy app` → `Success: no issues found in 105 source files`, rc=0. **[MEDIDO]** o gate é **PARCIAL** e isto está escrito no próprio item do plano: **28 dos 105** arquivos de `app/` estão sob `ignore_errors` e ficam fora de verificação; dos 77 restantes, 44 estão sob `strict` pleno e 33 sob o default. **[MEDIDO]** a lacuna de regressão é fechada pelo **shadow ratchet**: `Found 127 errors in 28 files (checked 105 source files)`, rc=1 — o orçamento de 127 está **intacto**. Números em `docs/quality/BASELINE.md` §6.3/§6.6/§6.8. **Não** ler esta linha como "o codebase está type-checked". |
| 5.4 | `pytest` passa | **PASS** | **[MEDIDO]** `pytest tests/ -q` → `264 passed, 48 deselected`, rc=0 (258 + os 6 desta task). Step bloqueante `Run tests` (`ci.yml:238-239`). |
| 5.5 | Coverage >= baseline | **PASS** | **[MEDIDO]** `pytest tests/ -q --cov=app --cov-precision=2 --cov-fail-under=59.19` → `TOTAL 6343 2573 59.44%` (3770/6343; cru 59,4356%), `Required test coverage of 59.19% reached.`, rc=0. Piso efetivo: **≥ 3755 statements cobertos** (3755 → 59,1991% → 59,20 passa; 3754 → 59,18 reprova). A folga era de **2 statements** no baseline e é de **15** aqui, porque o teste novo cobriu **13 statements** que estavam descobertos (medido: `missing_lines` de `article_parser.py` caiu de 133 para 120, em 13 linhas de fonte distintas). |
| 5.6 | Docker build passa no CI | **PASS (medido localmente)** | **[MEDIDO]** `docker build -f Dockerfile .` (comando literal de `ci.yml:351`) **passou**: `RC=0`, imagem `bhub-v1.1-release:latest` (8.66GB), passo final `[11/11]` concluído. Smoke test próprio: `docker run --rm --entrypoint python <img> -c "import app.main"` → `import app.main OK` (o CI **não** executa a imagem — é o achado M5). A rodada anterior falhava por **disco** (`No space left on device`, VM a 98%): após o cleanup autorizado de volumes anônimos, a VM foi a **77%** (12.5G livres) e o build passou. **[NÃO VERIFICADO] no runner do GitHub** — ver §10.1. |

---

## 6. Segurança (plano:1396–1403)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 6.1 | `.env` não está versionado | **PASS** | **[MEDIDO]** `git ls-files \| grep -E "(^\|/)\.env($\|\.)"` → apenas `.env.example` (raiz e backend). `.gitignore:36` ignora `.env` (e `:37-40` as variantes). |
| 6.2 | secrets vêm do ambiente | **PASS** | **[LIDO]** `docker-compose.prod.yml` não contém segredo literal: tudo vem de `${…}` do `.env`, e `SECRET_KEY=${SECRET_KEY:?defina SECRET_KEY no .env}` (`bhub-backend-python/docker-compose.prod.yml:35` e `:88`) **obriga** o operador a defini-la. `config.py:66` só tem valor default de placeholder, que é rejeitado (6.3). |
| 6.3 | produção rejeita configuração insegura | **PASS** | **[MEDIDO]** três rejeições reproduzidas com `ENVIRONMENT=production`: `DEBUG=true` → `ValidationError: DEBUG deve ser False em produção` (`config.py:189`); `ALLOWED_ORIGINS=*` → `Wildcards não são permitidos em ALLOWED_ORIGINS em produção` (`config.py:51-53`); `SECRET_KEY` default → `SECRET_KEY deve ser alterado em produção e ter pelo menos 32 caracteres` (`config.py:84-86`). Origem sem `http(s)://` e lista de origens vazia também são rejeitadas (`:49-53`, `:192-193`). **Quarta rejeição (F1, corrigido em §15):** `ENABLE_ARQ=false` em produção → `ENABLE_ARQ deve ser true em produção` (`config.py:195-203`). |
| 6.4 | headers de segurança permanecem ativos | **PASS** | **[LIDO]** `app/core/security_headers.py`: HSTS (`:66`), `X-Frame-Options: SAMEORIGIN` (`:71`), `X-Content-Type-Options: nosniff` (`:74`), `Referrer-Policy` (`:80`), CSP (`:88-94`). **[MEDIDO]** `tests/test_core_components.py:270,282` asserem `X-Frame-Options` e `content-security-policy`. |
| 6.5 | cookies de autenticação continuam HttpOnly/Secure em produção | **PASS** | **[LIDO]** `app/core/auth_cookie_middleware.py:25` → `cookie_secure = settings.is_production` (Secure só em produção, que é onde importa); `:63-65` e `:77-79` → `httponly=True`, `secure=self.cookie_secure`, `samesite="strict"`. **[MEDIDO]** as suítes de auth/cookie passam (`tests/test_auth_flow.py`, `tests/test_core_components.py`). **Nota de precisão:** os testes de `CookieTransport` usam `cookie_secure=False` explícito, logo o **valor** `Secure=True` em produção é **[LIDO]**, não asserido por teste. |
| 6.6 | consentimento e analytics não sofreram regressão | **PASS** | **[MEDIDO]** `pytest tests/test_analytics_consent_gate.py tests/test_cookie_consent_endpoints.py tests/test_cookie_consent_unit.py tests/test_legal_pages.py -q` → **70 passed**, rc=0. O gate de consentimento é `ENABLE_ANALYTICS=false` por default (`config.py:162`) e `ANALYTICS_RESPECT_DNT=true` no compose de produção. |

---

## 7. Observabilidade (plano:1407–1415)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 7.1 | healthcheck backend | **PASS** | **[LIDO]** endpoint `GET /health` (`app/main.py:350-358`); `Dockerfile:64` tem `HEALTHCHECK`; `docker-compose.prod.yml:55-59` usa `curl -f http://localhost:8000/health` (30s/10s/3 retries, `start_period: 60s`). **[MEDIDO]** `tests/test_smoke.py` cobre o health check. |
| 7.2 | healthcheck PostgreSQL | **PASS** | **[LIDO]** `docker-compose.prod.yml:126-130` → `pg_isready -U ${POSTGRES_USER:-bhub} -d ${POSTGRES_DB:-bhub}` (10s/5s/5 retries). |
| 7.3 | healthcheck Redis | **PASS** | **[LIDO]** `docker-compose.prod.yml:149-153` → `redis-cli ping` (10s/5s/5 retries). |
| 7.4 | worker observável | **PASS** | **[LIDO]** `@observed_job` nos **dois** jobs (`app/jobs/tasks.py:48` e o de classificação); métricas `arq.job.success` / `arq.job.failure` / `arq.job.duration` e span `arq.job` (`app/jobs/observe.py:50-64`; docstring `:10-13`). **[MEDIDO]** `tests/unit/test_arq_job_observability.py` 19 passed, incluindo `test_worker_startup_inicializa_telemetria_do_worker`. **[LIDO]** o serviço `arq-worker` desabilita `healthcheck` **de propósito** (`docker-compose.prod.yml:100-102`: o worker não tem servidor HTTP, a liveness é do ARQ + restart policy) — é decisão documentada, não lacuna. |
| 7.5 | logs possuem correlação suficiente para article/job | **PASS** | **[LIDO]** o log estruturado do job carrega `job_type`, `job_id`, `article_id`, `attempt`, `status`, `duration` e, na falha, `exception` (`app/jobs/observe.py:112-124`). **[MEDIDO]** asserido em `test_record_job_success_log_com_todos_os_campos` / `test_record_job_failure_log_com_exception`. |
| 7.6 | erros de fila aparecem nos logs | **PASS** | **[LIDO]** falha de enfileiramento emite `log.error` estruturado antes de propagar (`app/interfaces/task_queue.py:54-58`); falha de inicialização do pool em produção emite `arq_pool_init_failed` e re-levanta (`app/main.py:64-69`). **[MEDIDO]** `test_log_estruturado_em_falha_de_enfileiramento` (`tests/unit/test_task_dispatcher.py:330`). |
| 7.7 | métricas essenciais estão disponíveis | **PARCIAL — criadas, sem exportador de métricas** | **[LIDO]** as métricas são **criadas** (`app/core/telemetry.py:34-50`: `ai.classify.duration_ms`, `ai.fallback.total`, `feeds.articles.ingested.total`, `feeds.sync.failed.total`; `app/jobs/observe.py:50-64`) — mas **só** com `ENABLE_TELEMETRY=true`, e o default é `false` (`app/config.py:158`). **[LIDO]** e o `MeterProvider` é instalado **sem leitor/exportador** (`app/core/telemetry.py:31` — `metrics.set_meter_provider(MeterProvider())`, sem `PeriodicExportingMetricReader` nem exporter de métricas). Os **traces** são exportados via OTLP (`:19,:28`), as **métricas não**. Ou seja: os instrumentos existem em processo e são exercitados por teste, mas **não há caminho de exportação** para um backend de métricas. O item "estão disponíveis" não está satisfeito como capacidade operacional. |

---

## 8. Ingestão (plano:1419–1426)

| # | Item literal | Status | Evidência |
|---|---|---|---|
| 8.1 | Conditional GET continua funcionando | **PASS** | **[MEDIDO]** `tests/test_feed_aggregator_policy.py`: `test_not_modified_conta_como_sucesso_e_zera_erros` (`:86`) e `test_sync_ok_persiste_etag_e_last_modified` (`:115`), `test_fetch_recebe_etag_e_custom_headers_do_feed` (`:134`). **[LIDO]** as colunas `feeds.http_etag` / `http_last_modified` vêm da migração `009_feed_http_cache`. |
| 8.2 | Entrada inválida não aborta todo feed | **PASS** | **[MEDIDO]** `test_entrada_invalida_nao_aborta_o_feed` (`tests/integration/test_feed_pipeline.py:747`): com a 2ª de 3 entradas malformada, `success=True`, `error_count == 0` e os artigos **antes e depois** persistidos (savepoint por entrada em `app/services/feed_aggregator.py`). **Prova de mutação independente** (Task 15): removendo o savepoint o teste falha (`rc=1`). |
| 8.3 | Deduplicação atual continua funcionando | **PASS** | **[MEDIDO]** `test_duplicata_nao_gera_novo_artigo_nem_novo_job` (`test_feed_pipeline.py:649`): mesmo feed re-sincronizado → `new_articles == 0` **e** `errors == []`; a chave de dedupe é **por feed** (`feed_{feed_id}_{md5(guid)}`), com backstop global em `articles.doi` único. **Prova de mutação independente**: removida a pré-checagem, a asserção de `errors` é a que discrimina (`rc=1`). |
| 8.4 | Parsing de autores OJS possui teste de regressão | **PASS (fechado nesta task)** | **[MEDIDO]** a heurística de desmembramento existe em `app/services/article_parser.py:190-222` (ramo de split em `:210-220`). **[MEDIDO — estado inicial]** este item **falhava**: `grep -rn "OJS\|_extract_authors" tests/` → **0 testes** exercitavam a heurística, e `--cov-report=term-missing` mostrava as linhas **215-218** (o corpo do split) em `missing_lines` **tanto** na suíte unitária **quanto** na de integração. O commit que introduziu o comportamento (`d858451`, "desmembra listas de autores colapsadas pelo feedparser (feeds OJS)") não trouxe guarda. **Correção aplicada** (§11-F2): novo `tests/unit/test_article_parser_ojs_authors.py`, **6 testes** exercitando o caminho real (`feedparser.parse` → `_extract_authors`), pinando a heurística **nos dois sentidos** — lista colapsada deve ser dividida; `'de Rose, Júlio C.'`, `'Angela West, MS, BCBA'`, `'Helena de Freitas Rocha e Silva'` **não** podem ser divididos. **[MEDIDO]** GREEN: 6 passed, rc=0; as linhas **215-218 agora estão EXECUTED**. **[MEDIDO — prova de mutação em cópia `/tmp`, árvore intocada]** revertendo a heurística para `looks_like_list = False` (comportamento pré-`d858451`) → **3 failed, rc=1**; forçando `looks_like_list = True` (divide demais) → **2 failed, rc=1**. O teste sabe falhar nas duas direções. |
| 8.5 | Feed rediscovery possui teste de regressão | **PASS** | **[MEDIDO]** `tests/test_feed_rediscovery.py` — 4 testes: valida candidato e retorna URL, ignora candidato igual/inválido, sem `website_url` retorna `None`, e respeita a unique constraint. |
| 8.6 | Truncamento de campos não mascara corrupção silenciosa | **PARCIAL — o truncamento É silencioso** | **[MEDIDO]** `_truncate` (`app/services/feed_aggregator.py:23-32`) corta com `value[:max_length]` **sem nenhum log, aviso ou contador** quando trunca; as **8 chamadas** (`:325,326,329,331,332,333,336,337`) aplicam-no a `external_id`/`title`/`original_url`/`doi`/`journal_name`/`language`/`image_url`/`pdf_url`. **[MEDIDO]** `grep -rn "_truncate\|truncat" tests/` → **0 testes** de `_truncate` do agregador (o único hit é `_truncate_text` do OpenGraph, que é outra função). A intenção declarada na docstring (evitar `StringDataRightTruncationError` e não derrubar o flush) é cumprida, e isso é bom — mas "não mascara corrupção silenciosa" não: hoje um título de 900 caracteres é cortado a 500 **sem que ninguém saiba**. O item está satisfeito apenas na metade que impede a falha em cascata. |

---

## 9. Staging (plano:1430–1442)

**Seção inteira: NÃO VERIFICADA.** Não existe ambiente de staging neste repositório — só o guia
`docs/deploy/DEPLOY_STAGING.md`. Nenhum deploy de staging foi executado nesta verificação. O que
torna estes itens não verificáveis aqui **não** é a ausência de qualquer prova em código/teste — é
que o critério de cada um é o **ambiente de staging** (um deploy real, com restart e recuperação).
Quatro deles têm a mecânica provada em infraestrutura real descartável, o que **não** substitui a
prova em staging; o resto não tem cobertura alguma.

| # | Item literal | Status |
|---|---|---|
| 9.1 | Deploy limpo | **NÃO VERIFICADO** |
| 9.2 | Migrações aplicadas | **NÃO VERIFICADO** (o `upgrade head` em banco vazio está provado em 3.2 — **em container descartável, não em staging**) |
| 9.3 | Feed real sincronizado | **NÃO VERIFICADO** |
| 9.4 | Artigo novo persistido | **NÃO VERIFICADO** |
| 9.5 | Classificação executada via ARQ | **NÃO VERIFICADO** (provado em integração real — item 2.2 / §1.1 — não em staging) |
| 9.6 | PDF processado quando disponível | **NÃO VERIFICADO** (provado em integração real — item 2.3) |
| 9.7 | Busca encontra o artigo | **NÃO VERIFICADO** (provado no PostgreSQL real — §3.4/§3.5) |
| 9.8 | Restart backend | **NÃO VERIFICADO** |
| 9.9 | Restart worker | **NÃO VERIFICADO** |
| 9.10 | Restart Redis | **NÃO VERIFICADO** |
| 9.11 | Confirmar recuperação após restart | **NÃO VERIFICADO** |

---

## 10. Go / No-Go

O checklist define as condições literalmente (plano:1446–1472).

**Nota de escopo (a própria spec da Task 19 a delimita):** o comando do item é *"Verificar cada item
do checklist de release … **que é verificável no código/testes**"* (plano:1341). Os 11 itens de
**Staging** (§9) **não** são verificáveis em código/testes — exigem um ambiente externo. Isso é o
motivo de a spec pedir um status **"GO/NO-GO parcial"**, e não um GO cheio. A seção §9 é, portanto,
**fora do que a Task 19 pode verificar**, e está marcada como `NÃO VERIFICADO` — explicitamente, não
por omissão.

### 10.1 Condições de GO

| Condição | Situação | Evidência |
|---|---|---|
| CI verde | **PARCIAL — e o workflow NÃO pode rodar neste branch** | Os steps do `.github/workflows/ci.yml` foram **lidos** e executados **localmente**: lint/teste/type-check rc=0 (§1.1), `docker build` **PASS** após o cleanup (§5.6). **[MEDIDO]** o workflow dispara em `push: branches: [main]` e em `pull_request:` — e **nada mais**: o push de `feat/v1.1-reliability` **não gerou run** (`gh run list --branch feat/v1.1-reliability` vazio; 0 runs para o SHA do HEAD). Para haver execução hospedada é preciso um **PR** (ou push em `main`) — ver §16. **[NÃO VERIFICADO]** como execução hospedada. |
| staging verde | **NÃO — não executado** | §9 — nenhum item executado; fora do alcance de código/testes. |
| migrações verificadas | **SIM** | §3.2, §3.3, §3.4, §3.5 — PostgreSQL 16 real, banco vazio, cadeia completa e reversível. |
| fila persistente verificada | **SIM** | §4.3, §4.4, §2.2 — Redis 7 e worker ARQ reais; job persistido no Redis antes do consumo. |
| documentação atualizada | **SIM** | Task 17 (CURRENT_ARCHITECTURE + 5 ADRs) e Task 18 (varredura histórica + AGENTS/CLAUDE) completas e revisadas; invariantes de §12 revalidados. |

### 10.2 Condições de NO-GO

| Condição | Situação | Evidência |
|---|---|---|
| task crítica ainda usa fallback não persistente | **NÃO, na configuração de produção documentada** | §2.1 — em produção o ARQ está ligado (`docker-compose.prod.yml:34,:87`) e o `InlineTaskQueue` não é alcançado; o dispatcher **recusa** enfileirar sem pool (`task_dispatcher.py:82-89`) em vez de degradar. **Ressalva F1 resolvida (§15):** `ENVIRONMENT=production ENABLE_ARQ=false` passou a ser **rejeitado** pela config no startup — a lacuna de *validação de configuração* foi fechada. |
| migration falha em banco vazio | **NÃO** | §3.2 — passa, com `rc=0` asserido. |
| worker não recupera jobs | **NÃO VERIFICADO, não refutado** | §4.5 — a persistência do job está provada; o **restart** do worker não foi exercitado por teste algum. |
| CI permite lint/type-check falhar | **NÃO** | `ruff`, `format`, `mypy app`, o ratchet e o harness são steps **bloqueantes**; **0** `continue-on-error`. |

### 10.3 Status emitido

```text
GO/NO-GO PARCIAL  (o status que a própria Task 19 pede)

Verificação de CÓDIGO — o que a Task 19 manda verificar:   GO

  ITENS DE CÓDIGO/TESTE (§2-§8) = 42, contados na tabela:
      34 PASS
       5 PARCIAL   (3.6 pool não testado; 4.5 restart do worker não exercitado;
                    4.6 backlog sem superfície no app; 7.7 métricas sem exportador;
                    8.6 truncamento silencioso)
       2 NÃO VERIFICADO  (4.1 Redis em staging; 4.2 worker em staging)
       1 PASS medido localmente e NÃO VERIFICADO no runner (5.6 Docker build)
       0 FALHANDO  (o único que falhava — 8.4, teste de regressão OJS — foi
                    CORRIGIDO nesta task, com prova de mutação nas duas direções)
  ITENS DE STAGING (§9)          = 11, NÃO VERIFICADOS (exigem ambiente externo)
  TOTAL                          = 53 itens, todos com status e evidência

Liberação da RELEASE v1.1:                                 NO-GO
  - condição de GO "staging verde" NÃO satisfeita (não executada);
  - GitHub Actions nunca executados — 0 runs para este HEAD: o workflow só
    dispara em push de `main` e em `pull_request`, e o branch foi pushed sem PR (§10.1);
  - staging inexistente (nenhum ambiente/credencial; §9).

Critical aberto: 0     Important aberto: 0  (F1 corrigido — ver §11 e §15)
```

**Este NO-GO é sobre a liberação da release, não sobre o fechamento da Task 19.** O deliverable da
Task 19 é esta verificação; ela está completa e produz o veredito acima. Nenhum item foi marcado
como PASS sem evidência, nenhum gate foi relaxado para caber num GO, e nenhum problema foi escondido.

---

## 11. Achados desta verificação

Registrados com o mesmo destaque dos itens que passam. **Dois foram corrigidos:** o **F2**
(item de release falhando; fix é um arquivo de teste, sem tocar `app/`) e o **F1** (autorizado
na rodada de fechamento; fix é validação de configuração — ver §15). **Nenhum dos outros achados
foi corrigido**; a correção deles pertence a decisão registrada.

| ID | Achado | Severidade proposta | Evidência |
|---|---|---|---|
| **F1** | `ENVIRONMENT=production` + `ENABLE_ARQ=false` era **aceito** e o dispatcher devolvia `InlineTaskQueue` — produção podia ser configurada para o caminho não persistente sem rejeição (§2.1). **CORRIGIDO** (§15): `app/config.py` rejeita a combinação no startup. | **Important — RESOLVIDO** | **[MEDIDO]** antes: `ENVIRONMENT=production ENABLE_ARQ=false` → aceito, `queue chosen = InlineTaskQueue`, rc=0. Depois: `ValidationError: ENABLE_ARQ deve ser true em produção`. 6 testes em `tests/unit/test_config_production_arq.py`, prova de mutação (guard removido → 2 failed). |
| **F2** | O item **8.4** falhava: a heurística de desmembramento de autores OJS (`article_parser.py:190-222`) **não tinha teste de regressão**, e as linhas **215-218** estavam descobertas nas duas suítes; o commit `d858451` entregou comportamento sem guarda. **CORRIGIDO nesta task** (§8.4): `tests/unit/test_article_parser_ojs_authors.py`, 6 testes pelo caminho real, com prova de mutação nas duas direções (undersplit → 3 failed; oversplit → 2 failed). Nenhuma linha de `app/` foi tocada. | **Important — RESOLVIDO** | **[MEDIDO]** `--cov-report=term-missing` (unit e integração) listava `215-218`; hoje `EXECUTED`. |
| **F3** | O item **3.6** pede pool "configurado **e testado**": está configurado (`database.py:28-33`) e **não** testado (0 asserções em `tests/`). | Minor | **[MEDIDO]** grep em `tests/` → 0 hits. |
| **F4** | O item **7.7**: as métricas são criadas mas o `MeterProvider` não tem exportador (`telemetry.py:31`), e `ENABLE_TELEMETRY` é `false` por default. | Minor | **[LIDO]** `telemetry.py:19-31`. |
| **F5** | O item **8.6**: `_truncate` corta silenciosamente, sem log/contador. | Minor | **[MEDIDO]** `feed_aggregator.py:23-32`, **8** chamadas, 0 testes. |
| **F6** | O item **4.5** (restart do worker) e **4.6** (backlog) não têm cobertura: não existe teste de restart nem superfície de backlog no app. | Minor | **[MEDIDO]** greps em `tests/integration/` e `app/`. |
| **F7** | Existem **3** arquivos compose e **2** se chamam "prod"; o da raiz fixa SQLite (`:31`) e monta um `./Frontend` que não existe (`:86`). A ambiguidade está **documentada** (não resolvida) — ver §14. | Observation | **[MEDIDO]** `docker-compose.prod.yml:31,:86`; `bhub-backend-python/docker-compose.prod.yml:32`. |
| **F8** | **1 link local quebrado** encontrado: `docs/ui-ux/UI_UX_SETUP.md:157` → `./GUIA_INICIO_RAPIDO.md` (o alvo real é `docs/configuracao/GUIA_INICIO_RAPIDO.md`). **Pré-existente**, fora dos arquivos tocados pelas Tasks 17/18 (o arquivo não aparece no diff `d6c3fc9..9091bc8`). | Minor | **[MEDIDO]** detector próprio: 194 links conferidos (excluindo este artefato), 1 quebrado — **idêntico** no baseline `9091bc8`. |

---

## 12. Invariantes de documentação (revalidados)

Revalidados **por medição** nesta verificação, porque a Task 19 edita `docs/`. A forma de medir foi
escolhida para ser **imune à autorreferência**: este próprio documento contém os termos
(`SQLite`, `produção`, `create_task`), então o número absoluto do repositório muda a cada edição
dele e não é evidência de nada. O que é evidência é a comparação **excluindo este arquivo**:

```text
MÉTRICA ESTÁVEL — repositório versionado, EXCLUINDO este artefato

Comando (rodado VERBATIM nos dois estados; restrito aos `.md` RASTREADOS via
`git ls-files`, para não capturar os `.md` gitignorados que existem no diretório
de trabalho, e excluindo este artefato, que contém os próprios termos):

  git ls-files -z '*.md' | tr '\0' '\n' | grep -v 'RELEASE_CHECKLIST' \
    | xargs grep -niE "sqlite[^.]{0,70}(produ[cç][aã]o|production)|(produ[cç][aã]o|production)[^.]{0,70}sqlite" | wc -l

  git ls-files -z '*.md' | tr '\0' '\n' | grep -v 'RELEASE_CHECKLIST' \
    | xargs grep -niI "create_task" | wc -l

Cada um devolveu 29 e 42 no HEAD e 29 e 42 no baseline. Sem o filtro de
rastreados, o mesmo regex varre também os `.md` do diretório de trabalho e
devolve outro número (94, com o `--exclude` do artefato; 97 sem ele) — por isso o
escopo é declarado.

Escopo: 95 `.md` rastreados no HEAD (94 no baseline), menos este artefato. A
escolha do escopo é declarada porque o número é sensível a ela — outros escopos
(ex.: sem o filtro de rastreamento) dão outros valores.

SQLite-as-production    baseline 9091bc8: 29 linhas
                        HEAD:              29 linhas    IDÊNTICO
create_task             baseline 9091bc8: 42 linhas
                        HEAD:              42 linhas    IDÊNTICO

Conferido por CONJUNTO, não só por contagem: as 29 linhas (e as 42) são as mesmas
entre os dois estados — nenhuma linha entrou ou saiu. O diff da task altera só
índices (`docs/architecture/ROADMAP.md` +8/−4 e `docs/README.md` +1, ambos
reescritos para apontar ao artefato criado) e cria 2 arquivos novos (este artefato
e o teste do item 8.4); nenhuma das linhas que pontua está entre as alteradas.

0 asserções não qualificadas em ambos os contadores: cada linha que pontua foi
lida no contexto e é negação explícita, qualificador dev/testes, alternativa
REJEITADA dentro de ADR, documento com banner STATUS: HISTÓRICO + caveat inline,
risco registrado, ou a metalinguagem deste próprio §12 (que não afirma nada sobre
o banco nem sobre a estratégia de jobs).

Broken local links (detector próprio):  1  (F8, PRÉ-EXISTENTE)
  - 194 links conferidos excluindo este arquivo / 196 incluindo-o;
  - baseline 9091bc8: 1 (docs/ui-ux/UI_UX_SETUP.md:157 -> ./GUIA_INICIO_RAPIDO.md)
  - estado atual:     1 (o MESMO link, no mesmo arquivo, não tocado por esta task)
  → o link novo deste artefato e os de docs/architecture/ROADMAP.md e docs/README.md resolvem.
Missing referenced paths citados como existentes:              0
```

## 13. Riscos conhecidos (permanecem riscos — não foram corrigidos)

Fonte: `docs/architecture/CURRENT_ARCHITECTURE.md` §13 e `docs/architecture/ROADMAP.md` §3. Nada aqui foi implementado por esta
verificação.

| Risco | Status | Impacto na liberação |
|---|---|---|
| `R-01` — sem outbox entre `commit` e despacho | **DEFERRED** | Janela em que o artigo fica persistido e o job se perde, sem retry. Ordem correta, **atomicidade inexistente**. Aceito fora do contrato da milestone. |
| `R-02` (T16-F1) — TOCTOU na dedupe de PDF por hash | **DEFERRED** | Falha **terminal, sem retry**; o artigo perdedor pode ficar **sem PDF**. Medido 5/5 tentativas. Defeito de produto, fora do contrato literal da Task 16. |
| `R-03` (RED-3) — `max_tries`/`retry_jobs` mortos | **DEFERRED** | Retry é mecanismo provado, mas **não** vale para os dois jobs do repo. Ver §4.3. |
| `R-04` (RED-5) — startup do worker ~12 s + rede | **DEFERRED** | Custo e dependência de rede no boot do worker. |
| `R-05` — rate limiting de `POST /api/v1/ai/translate` | **DEFERRED** | O slowapi procura um parâmetro `request` que ali é o corpo Pydantic; a proteção **não opera** nessa rota. Sinalizado desde a Task 9, sem dono. |
| `R-06` — `get_or_create_category` check-then-act | **DEFERRED** | Mesma forma do defeito corrigido no 14.G, contra outra constraint. |
| `R-07` — limite inerente do ratchet por contagem | **DEFERRED** | Outras relaxações (`disable_error_code`, `follow_imports`) baixam o total sem serem pegas. Conserto estrutural nomeado. |
| `R-08` (N1/Task 13) — teste de ordenação depende do plano do PG | **DEFERRED** | Capacidade de falhar do teste varia com o plano de consulta. |
| `R-09` — `skipped` ambíguo no pipeline de PDF | **DEFERRED** | Confunde "nada a fazer" com "download/extração falhou". `ProcessingStatus.FAILED` é código morto nesse caminho. |
| `R-10` — templates ainda anunciam SQLite | **DEFERRED** | Copy de produção em `app/templates/`. |
| `R-11` — backup automático não cobre o PostgreSQL | **DEFERRED** | — |
| `R-12` — modo `semantic` usa motor só de dev | **DEFERRED** | — |
| `.dockerignore` inexistente | **DEFERRED** | `COPY . .` leva a árvore inteira para o contexto de build. |
| Cenários 25/29/31 do harness | **DEFERRED** | Casos de tabela inline com TOML inválido (as asserções de guard valem). |
| M5 (Task 11) | **DEFERRED** | O CI constrói a imagem mas não a executa; nesta rodada o build foi executado **localmente** e parou por **disco**, não por código (§5.6). |

---

## 14. Fora de escopo (não tocado por esta verificação)

- **UI/UX:** o redesenho de UI/UX é um ciclo **encerrado** cujos documentos estão marcados como
  históricos (`docs/architecture/CURRENT_ARCHITECTURE.md` §14, `docs/architecture/ROADMAP.md` §4) e a modernização visual é trabalho
  **fora do contrato desta milestone** — nenhum template, estilo, navegação ou design system foi
  alterado por esta verificação (medido: 0 arquivos de UI/templates/css/js no diff). Qualquer
  achado visual pertence a uma milestone própria; nenhuma foi especificada aqui.
- **Ambiguidade dos composes (F7):** documentada, **não** resolvida — escolher uma variante canônica
  é decisão de produto, não desta task.
- **Push / tag:** o roadmap **não** pede tag nem versão nova. Nenhuma foi criada.

---

## 15. F1 — correção autorizada (rodada de fechamento)

O F1 deixou de ser um risco a adjudicar: na rodada de fechamento sua correção foi **autorizada** e
implementada. Produção passa a exigir ARQ **por validação de configuração**.

**O que mudou:** `app/config.py`, dentro do `validate_production_settings` que já existia (`:183`) —
a validação central e precoce do projeto. Reusa o `is_production` (`:180`) existente; nenhum conceito
novo de environment foi criado. Não há `PING` de Redis no startup (não é política de
disponibilidade — é corretude de configuração).

```text
production + ENABLE_ARQ=false        → rejeitado no startup (fail fast)
production + ENABLE_ARQ ausente      → rejeitado (default do modelo é false, `:63`)
production + ENABLE_ARQ=true         → aceito
development / staging + false        → aceito (executor inline preservado)
```

**O executor inline não foi removido** — `InlineTaskQueue` segue sendo a fila de dev/test.

| Cenário | Esperado | Observado | Status |
|---|---|---|---|
| `production` + `false` | rejeitar | `ValidationError: ENABLE_ARQ deve ser true em produção` | PASS |
| `production` + ausente | rejeitar | idem (default `false` em `app/config.py:63`) | PASS |
| `production` + `true` | aceitar | `enable_arq=True` | PASS |
| `development` + `false` | aceitar | fila = `InlineTaskQueue` | PASS |
| `staging` + `false` | aceitar | `enable_arq=False` | PASS |

**Sobre o caso `test` do plano:** `test` **não** é um environment válido neste projeto — o
`Literal` em `app/config.py:28` aceita apenas `development`, `staging`, `production`. A suíte roda
como `development` (o default), que é aceito com `ENABLE_ARQ=false`. Não foi criado um segundo
conceito de environment para cobrir o rótulo: o mapeamento está declarado no teste
(`test_test_nao_e_um_environment_valido`).

**Sem fallback silencioso no runtime (medido):** com ARQ ligado, falha de enfileiramento levanta erro
explícito (`ArqTaskQueue._enqueue` termina em `raise`, com log estruturado) — não degrada para
inline. O único `asyncio.create_task` executável do app está dentro de `InlineTaskQueue._run_inline`
(`app/interfaces/task_queue.py:91`). `runtime silent fallback: NOT PRESENT`. Nada foi alterado nesse
eixo.

**Custo em `app/`:** 10 linhas adicionadas em um único arquivo. É a **primeira** mudança de `app/` da
Task 19 — as anteriores eram 0; registrado para que o número não seja lido como se valesse para a
task inteira.

---

## 16. Gates externos de release (executados sob autorização)

Medidos após a autorização da rodada de fechamento. **Nenhum estado desconhecido foi promovido a PASS.**

| Gate | Status | Evidência |
|---|---|---|
| **Build** | **PASS (local) / NÃO VERIFICADO (runner)** | `docker build -f Dockerfile .` (literal de `ci.yml:351`) → `RC=0`, imagem `bhub-v1.1-release:latest` (8.66GB), `import app.main` OK. A rodada anterior falhava por **disco** (VM a 98%, `No space left on device`); após o cleanup autorizado, a VM foi a **77%** (12.5G livres) e o build passou. |
| **GitHub Actions** | **NOT VERIFIED** | **0 runs para o SHA do HEAD.** O workflow dispara em `push: branches: [main]` e em `pull_request:` — o push do branch **não gera run**. Leitura do YAML **não** é execução hospedada. |
| **Staging** | **NOT VERIFIED** | Nenhum ambiente de staging existe/acessível. Não há compose de staging, nenhuma variável de staging no ambiente, e o único documento (`docs/deploy/DEPLOY_STAGING.md`) está marcado **HISTÓRICO** (era SQLite, exige VPS/SSH). Não simulado localmente: simular e chamar de staging real seria falso. |

### 16.1 Cleanup de Docker (autorizado, lista explícita)

- **Inventariado antes de remover**: 461 volumes dangling = **414 anônimos** (label `com.docker.volume.anonymous`, sem container associado) + **47 NOMEADOS**.
- **Os 47 nomeados NÃO foram tocados** — incluem dados persistentes do projeto (`bhub_db_data`, `bhub_redis_data`, `bhub_backend_postgres_dev_data`), de outros projetos (`aba-clinic-system_*`, `infra_*`, `khoj_*`) e do `supabase` que está **rodando**.
- **Removidos**: os **414 anônimos**, por lista explícita (sem `system prune`, sem `--all`, sem `-a`), com os containers ativos conferidos antes e a interseção com volumes em uso verificada como **vazia**. `rc=0`, 0 erros.
- **Espaço**: VM **1.1G → 12.5G livres** (`98% → 77%`); `Local Volumes` **16.14GB → 3.76GB**. Dados do BHub conferidos como presentes depois.
- **Não removido**: imagens dangling e build cache (não foram necessários ao build).

### 16.2 Git

- Push **normal** de `feat/v1.1-reliability` com upstream configurado. Sem force, sem merge em `main`, sem tag, sem release.
- Remoto confirmado apontando para o HEAD local; `main` no `origin` segue em **`1d3177e`** (intocado).
- Nenhum arquivo sensível nos commits enviados (`.env` não versionado; só `.env.example`).

### 16.3 O que destrava o Actions

**Não é o push — é um PR.** O workflow só dispara em `push` para `main` ou em `pull_request`. Criar o PR (ou mergear) é **ação de release** e não foi autorizada nesta rodada: está registrado como o próximo passo humano, e é o que falta para transformar o Actions de `NOT VERIFIED` em PASS/FAIL medido.
