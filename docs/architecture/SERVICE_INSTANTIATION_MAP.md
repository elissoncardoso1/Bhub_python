# Mapa de Instanciação de Serviços — BHub v1.1 (T2.1)

> **Status:** ATIVO · **Escopo:** `bhub-backend-python/app` · **Data:** 2026-09-15
> Task 5 do plano BHub v1.1 — Production Reliability (épico 2, T2.1).
> Insumo para as tasks 6–8 (injeção de dependências em PDF/OpenGraph/Feed e
> teste de `dependency_overrides`).

## Regra de classificação

| Classe | Definição | Ação |
|---|---|---|
| **PURE** | Parsers/normalizadores/formatters/validators sem I/O externo (sem banco, rede, filesystem, Redis, IA externa, fila ou cache) | Instanciação direta **aceitável** |
| **I/O** | Serviço com dependência real de banco/rede/filesystem/Redis/API externa/IA/fila/cache — **verificada no código** | **Preferir injeção** (`app/api/deps.py` + `Depends()`) |
| **LEGACY** | Instanciação em camada legada, duplicada de caminho novo, ou singleton/global a decidir | **Marcar para decisão** |

Importante: a classificação abaixo foi atribuída lendo o código de cada serviço
(construtor, métodos e imports), **não por presunção de nome**. Nenhum código de
produção foi alterado nesta task — o mapa é analítico.

---

## 1. Mapa por ocorrência

### 1.1 ArticleParserService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/services/feed_aggregator.py:41` (`self.parser = ArticleParserService()`) | **PURE** | Nenhum. Apenas `re`, `html`, `hashlib`, `bs4`, `dateutil` sobre dicts de entrada (`app/services/article_parser.py` — sem imports de db/rede/fs) | **Manter direto.** Parser puro; não acoplar ao FastAPI (critério de aceite do épico) |

### 1.2 FeedFetcher

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/services/feed_aggregator.py:50` (`self.fetcher = FeedFetcher()`) | **I/O** | Rede. Constrói `httpx.AsyncClient` quando `client=None` (`app/services/feed_fetcher.py:54-56`); usin em `aggregator.fetch()`/`_rediscover_feed_url` (linhas 413, 485, 499) | **Injetar.** `FeedFetcher.__init__` já aceita `client: httpx.AsyncClient \| None` — o `FeedAggregatorService` deve repassar um client (ou a própria instância) recebido por parâmetro, permitindo fake nos testes (task 7/8) |

### 1.3 FeedAggregatorService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/api/deps.py:90` (`get_feed_aggregator_service`) | **I/O** ✓ já injetado | Banco (AsyncSession), rede (`httpx.AsyncClient` próprio l.42, `FeedFetcher` l.50), Redis/fila via `dispatch_*` (`task_dispatcher`) | **Manter** — já é `Depends()` com `yield`/`close()` (`FeedAggDep`); usado em `app/api/v1/admin/feeds.py:161,174,197` |
| `app/web/admin.py:144` (`service = FeedAggregatorService(db)`) | **LEGACY** | Mesmo I/O acima; camada web contorna `deps.py` e chama `close()` manualmente em `try/finally` (l.162-163) | **Decidir:** reutilizar `FeedAggDep` (FastAPI web routes suportam `Depends`) ou extrair factory comum. Evita duplicar o ciclo de vida |
| `app/jobs/scheduler.py:29` (`service = FeedAggregatorService(db)`) | **I/O** | Banco (sessão do `get_session_context`), rede (2 clients HTTP), fila. Fora do contexto FastAPI — não há `Depends()` disponível | **Injetar via parâmetro/factory**, não `Depends()`: scheduler é processo/loop próprio; passar `parser`/`fetcher` como argumentos construtores quando o agregador aceitar (task 7). Instanciação direta é aceitável **desde que** as dependências internas sejam substituíveis |

### 1.4 PDFService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/api/v1/admin/articles.py:187` (`admin_delete_article` → `pdf_service = PDFService()`) | **I/O** | Filesystem: `delete_pdf` remove arquivo do disco (`app/services/pdf_service.py:331`) | **Injetar** via provider em `deps.py` (task 6) — storage fake nos testes |
| `app/api/v1/admin/articles.py:240` (`admin_upload_pdf` → `pdf_service = PDFService()`) | **I/O** | Filesystem (`save_path.write_bytes`, l.75-77), banco (`check_duplicate` l.320, persistência do feed/artigo), e rede indireta não neste fluxo | **Injetar** (task 6) |
| `app/jobs/tasks.py:64` (`task_download_pdf` → `pdf_service = PDFService()`) | **I/O** | Filesystem + rede (`download_pdf_from_url` cria `httpx.AsyncClient` l.565) + banco (`process_article_pdf` via `get_session_context` ou sessão do job) | **Injetar via parâmetro/factory** — worker ARQ não tem `Depends()`; receber a instância (ou um storage/client) do contexto do job |
| `app/interfaces/task_queue.py:117` (`InlineTaskQueue.dispatch_pdf` → `service = PDFService()`) | **I/O** | Mesmo que `task_download_pdf` (mesma operação transacional) | **Injetar via parâmetro/factory** no executor inline (task 6) |

Nota: `PDFService.__init__` (l.28-29) só lê `settings.pdf_upload_path`; todo o I/O
acontece nos métodos. A injeção útil é de **storage (upload_path) e client HTTP**,
não da sessão (que já trafega como argumento `db`).

### 1.5 OpenGraphService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/services/opengraph_service.py:348` (`get_opengraph_service` provider) | **I/O** ✓ provider existe | Banco: `get_article_metadata` abre `get_session_context()` (l.229) e consulta `Article`; filesystem: `__init__` faz `mkdir` do cache dir (l.33-35) e `img.save(cache_path)` (l.341); fontes lidas do SO (l.40-51) | **Injetar** — provider já é `Depends()` usado em `app/api/v1/opengraph.py` (5 endpoints), mas **cria instância nova por request** (sem cache) e a dependência de banco está **oculta** (abre sessão própria em vez de receber `db`) — task 7 |
| `app/web/routes.py:728` (`og_service = OpenGraphService()` em rota web `article_detail`) | **LEGACY** | Mesmo I/O acima; duplica o caminho do provider sem `Depends()` | **Decidir:** usar `Depends(get_opengraph_service)` na rota web (rotas FastAPI suportam) ou unificar o provider em `deps.py`. Além disso, cada chamada recria o cache dir — ver task 7 |

### 1.6 SearchService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/api/deps.py:80` (`get_search_service`) | **I/O** ✓ já injetado | Banco: `self.db` AsyncSession, queries FTS5/TSVECTOR (`app/services/search_service.py:19`) | **Manter** (`SearchDep` usado em `app/api/v1/search.py` e `articles.py`) |
| `app/web/routes.py:84` (`search_service = SearchService(db)`) | **LEGACY** | Mesmo I/O; camada web contorna `deps.py` | **Decidir:** usar `SearchDep` na rota web (elimina duplicação de provider) |
| `app/web/routes.py:495` (`service = SearchService(db)` em sugestões) | **LEGACY** | Mesmo acima | **Decidir:** idem |

`SearchService` recebe a sessão por construtor — o I/O é explícito; a questão
aqui é apenas consistência (web vs API usam caminhos diferentes).

### 1.7 ClassificationService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/api/deps.py:73` (`get_classification_service`) | **I/O** ✓ já injetado | Banco (`self.db`), IA externa via `ai_manager` (rede nos providers), ML local (modelo em memória/disco) | **Manter** (`ClassifierDep`) |
| `app/jobs/tasks.py:32` (`task_classify_article`) | **I/O** | Mesmo acima; worker ARQ recebe `db` do contexto e chama `get_ai_manager()` (singleton) | Aceitável no worker (sem FastAPI); **preferir** receber `ai_manager` do contexto do job quando disponível, para permitir fake sem monkey-patch |
| `app/services/background_tasks.py:46` (`ClassificationService.classify_with_multiple_categories(...)` — classmethod, sem instância) | **LEGACY** | Banco (db passado como arg), IA via `get_ai_manager()` singleton importado localmente (l.39,43) | **LEGACY a decidir:** fluxo de classificação em background duplica a lógica do job ARQ (`task_classify_article`) com chamada estática. Avaliar deprecação em favor do `ITaskQueue` (T1.x) |

### 1.8 WebScrapingService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/api/v1/admin/articles.py:340` (`admin_scrape_url` → `scraper = WebScrapingService()`) | **I/O** | Rede: `__init__` cria `httpx.AsyncClient` próprio (`app/services/web_scraper.py:98-104`); `scrape_url` faz GET no site alvo | **Injetar** — aceitar `client` opcional (como `FeedFetcher`) e provider em `deps.py`; rota hoje precisa de `close()` manual duplicado no try e no except (l.344, 418) |

### 1.9 RefreshTokenService — instância global

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/core/refresh_token.py:285` (`refresh_token_service = RefreshTokenService()` — singleton global do módulo) | **LEGACY** | Banco indireto: todos os métodos que tocam persistência recebem `db` como argumento (`refresh_access_token(db, ...)`, `revoke_refresh_token(db, ...)`) — o objeto em si **não** guarda estado de I/O; `__init__` (l.25-27) só define `cookie_name`/`token_length` | **LEGACY a decidir (task 8):** é singleton module-level importado por `app/web/auth.py`, `app/api/auth/__init__.py` e `app/core/refresh_token.py` (helpers `get_refresh_token_from_request`/`validate_and_refresh_token`). Por ser **stateless** (toda I/O vem por argumento), o risco de estado global mutável é baixo; a opção de virar `Depends()` é válida mas de baixo ganho. Recomendação preliminar: **manter**, documentando que não há estado mutável |

### 1.10 AIManager / provedores de IA — singletons globais

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/ai/manager.py:455` (`_ai_manager` lazy global + `get_ai_manager()`) | **I/O** | Rede: `DeepSeekService`/`OpenRouterService`/`HuggingFaceService` criam `httpx.AsyncClient` por chamada (`manager.py:224,275,311,358,395,432`) | **Injetar.** `deps.get_ai_manager` já existe como `AIDep`; os call sites abaixo contornam: converter gradualmente para `Depends(AIDep)` (rotas) / parâmetro (jobs) |
| `app/api/v1/ai.py:70,161,198` (`ai_manager = get_ai_manager()`) | **I/O** | Idem (rotas `/translate`, `/classify`, `/status`) | Usar `AIDep` |
| `app/web/translation.py:62` | **I/O** | Idem | Usar `AIDep` na rota web |
| `app/ml/impact_rating.py:87` | **I/O** | Idem (uso hoje é "futuro", não efetivo — só checa `providers`) | Manter por ora (não efetiva) |
| `app/services/background_tasks.py:43` | **I/O** | Idem | Ver item 1.7 — fluxo legado |
| `app/ai/manager.py:43,51,55,59` (`LocalLLMService()`, `DeepSeekService()`, `OpenRouterService()`, `HuggingFaceService()` dentro de `_setup_providers`) | **I/O** | Rede (3 provedores externos) e filesystem/modelo local: `LocalLLMService._get_llm` usa **global** `_llm_instance: Llama` com lock (`local_llm_service.py:21,115-148`) e `get_model_manager()` | Aceitável: providers são interna do facade `AIManager` (contrato `IAIManager` já permite fake). Global `_llm_instance` é cache intencional do modelo — **não** é dependência a injetar |

### 1.11 ModelManager — singleton global

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/ai/model_manager.py:247` (`_model_manager` lazy global + `get_model_manager()`) | **I/O** | Filesystem (`models_dir.mkdir`, leitura de GGUF l.192) + rede (download do HuggingFace via `hf_hub_download`/`snapshot_download`) | **Manter como singleton lazy** — usado só por `LocalLLMService` (l.99,111); cache de modelos é caso legítimo de global imutável-após-init. Não expor em rotas |

### 1.12 EmbeddingClassifier / HeuristicClassifier

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/ml/embedding_classifier.py:19` — `EmbeddingClassifier` com `__new__` **singleton** (`_instance`) e estado de classe (`_model`, `_initialized`) | **I/O** | Disco/rede: `initialize()` carrega `SentenceTransformer(settings.embedding_model)` (l.39) — download do modelo no primeiro uso; `_model.encode` é CPU/memory | **Manter** — singleton de modelo caro é legítimo; já é substituível em teste via `EmbeddingClassifier.classify` (classmethods). Não acoplar ao FastAPI |
| `app/api/v1/ai.py:83` (`classifier = EmbeddingClassifier()`) | **I/O** (via singleton) | Idem — rota `/classify` faz fallback local | Aceitável: singleton devolve sempre a mesma instância; para teste de rota, `dependency_overrides` não se aplica (não é Depends). Se task 6/7 exigir fake aqui, extrair provider |
| `app/api/v1/ai.py:199` (`/status`) | Idem | Idem | Manter (endpoint de diagnóstico) |
| `app/ml/embedding_classifier.py:298` (`get_classifier()` helper) | **I/O** | Idem — **sem call sites em `app/`** (grep não encontrou uso) | **LEGACY a decidir:** helper sem uso — remover ou usar como ponto único de inicialização |
| `HeuristicClassifier` (`embedding_classifier.py:207`) — usado via classmethod estático (`classification_service.py:48`, `api/v1/ai.py:90`) | **PURE** | Regex/keywords em memória, sem banco/rede/fs | **Manter direto** |

### 1.13 TranslationCacheService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/web/translation.py:55,57,69` e `app/api/v1/ai.py:125+` (chamadas **estáticas** `TranslationCacheService.get_cached_translation(db, ...)`) | **I/O** | Banco: todos os métodos são `@staticmethod` que recebem `session: AsyncSession` (translation_cache_service.py:72-195) — I/O explícito, sem instância | **Manter** — não há instanciação; a sessão trafega como argumento. Nada a injetar além do `db` que as rotas já recebem |

### 1.14 AnalyticsService

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/web/admin.py:100-106` e `app/core/analytics_middleware.py:128,168,176` (chamadas estáticas `AnalyticsService.*`) | **I/O** | Banco: métodos recebem `db`/`session` como argumento (analytics_service.py:33+) | **Manter** — sem instanciação; sessão explícita |

### 1.15 Outros objetos com I/O relevante (fora do padrão `Service()`)

| Onde | Classificação | I/O real verificado | Recomendação |
|---|---|---|---|
| `app/services/feed_aggregator.py:42` — `httpx.AsyncClient` criado no construtor do agregador (usado em l.292 p/ buscar página do artigo) | **I/O** | Rede | **Injetar** — construtor deve aceitar client opcional (paridade com `FeedFetcher`); task 7 |
| `app/services/pdf_service.py:565` — `httpx.AsyncClient` criado por download em `download_pdf_from_url` | **I/O** | Rede | **Injetar** — `PDFService` aceitar client opcional; task 6 |
| `app/core/alerting.py:20` — `httpx.Client` síncrono no sink de alerta (criado 1× em `setup_logging`) | **I/O** | Rede (webhook) | **Manter** — infraestrutura de logging, fora do fluxo de request; best-effort por design |
| `app/core/limiter.py:10` — `limiter = Limiter(...)` global (slowapi) | **I/O** | Memória (in-memory); a API do slowapi exige instância global registrada no app | **Manter** — padrão da biblioteca |
| `app/jobs/scheduler.py:14` — `scheduler = AsyncIOScheduler(...)` global | **I/O** | Fila de jobs; inicializado/fechado em `setup_scheduler`/shutdown do app | **Manter** — singleton de infraestrutura com ciclo de vida controlado em `app/main.py` |
| `app/services/task_dispatcher.py:22-23` — globais `_arq_pool` (pool ARQ/Redis) e `_inline_queue` | **I/O** | Redis (pool ARQ) / event loop (inline) | **Manter** — design T1.1/T1.2 (fila explícita, sem fallback silencioso); fechados em `close_task_queue()` no shutdown |

---

## 2. Resumo

| Classificação | Ocorrências |
|---|---|
| **PURE** | 2 (`ArticleParserService` no agregador; `HeuristicClassifier` estático) |
| **I/O** | 31 (PDFService ×4, OpenGraphService provider, FeedFetcher no agregador, FeedAggregator em deps/scheduler, WebScrapingService, SearchService em deps, ClassificationService em deps/jobs, `get_ai_manager()` ×6, ModelManager singleton, EmbeddingClassifier singleton + 2 rotas, clients httpx do agregador/pdf_service, alerting/limiter/scheduler/pool ARQ) |
| **LEGACY** | 6 (FeedAggregator em web/admin, OpenGraph em web/routes, SearchService em web/routes ×2, classificação estática em background_tasks, singleton `refresh_token_service`) |

Total: 39 ocorrências mapeadas (contagem por linha da seção 1; a linha "Idem"
de `app/api/v1/ai.py:199` herda a classificação I/O da linha anterior).
O helper sem uso `get_classifier()` (1.12) não recebe linha própria — já
contabilizado nas linhas do EmbeddingClassifier.

## 3. Priorização recomendada para as tasks 6–8

1. **Task 6 (PDF):** injetar storage/client em `PDFService` e criar provider em
   `deps.py`; cobrir os 4 call sites (`admin/articles.py:187,240`,
   `jobs/tasks.py:64`, `interfaces/task_queue.py:117`) — os dois últimos via
   factory/parâmetro (sem FastAPI).
2. **Task 7 (OpenGraph + Feed):** `OpenGraphService` deve receber `db`
   explicitamente (hoje abre sessão própria) e o client HTTP/fetcher do
   `FeedAggregatorService` deve ser injetável; unificar o call site legado de
   `web/routes.py:728` no provider existente.
3. **Task 8 (globais):** decidir o destino de `refresh_token_service`
   (stateless → candidado a manter, apenas documentar), `_ai_manager`
   (converter rotas a `AIDep` gradualmente) e marcar `background_tasks.py`
   como legado a deprecar em favor do `ITaskQueue`.

Regra prática para código novo: **PURE → direto; I/O → provider em `deps.py`
(rotas) ou factory/parâmetro (jobs/scheduler); LEGACY → não copiar o padrão.**