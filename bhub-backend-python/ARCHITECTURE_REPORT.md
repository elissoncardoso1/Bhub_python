# Relatório de Arquitetura de Software — BHub Backend (Python)

**Data da Análise:** 06 de Maio de 2026
**Versão do Sistema:** 1.0.0
**Repositório:** `bhub-backend-python/`
**Total de Arquivos Python:** 144 (~18.800 linhas)

---

## 1. Visão Geral da Arquitetura

O backend do BHub é um **monolito modular** desenvolvido em **Python 3.12+** com **FastAPI** (>=0.115.0), servido via **Uvicorn**. A aplicação implementa arquitetura assíncrona com clara separação de responsabilidades organizada nas seguintes camadas:

```
┌─────────────────────────────────────────────────────────┐
│                    ENTRY POINTS                          │
│  app/main.py (353 linhas) — lifespan, middlewares, app  │
├─────────────────────────────────────────────────────────┤
│              API Layer (app/api/)                        │
│  REST JSON endpoints (/api/v1/*) + Auth + Users         │
├─────────────────────────────────────────────────────────┤
│              Web Layer (app/web/)                        │
│  SSR com Jinja2 + HTMX — páginas públicas e admin       │
├─────────────────────────────────────────────────────────┤
│           Services Layer (app/services/)                 │
│  Lógica de negócio: feeds, artigos, busca, PDF, IA      │
├─────────────────────────────────────────────────────────┤
│           AI / ML Layer (app/ai/, app/ml/)               │
│  Multi-provider LLM + embeddings + impacto               │
├─────────────────────────────────────────────────────────┤
│           Core Layer (app/core/)                         │
│  Segurança, CSRF, rate limiting, logging, analytics     │
├─────────────────────────────────────────────────────────┤
│           Data Layer (app/models/)                       │
│  SQLAlchemy 2.0 async ORM — 15 modelos                  │
├─────────────────────────────────────────────────────────┤
│           Infrastructure                                 │
│  SQLite + Alembic + APScheduler + Docker                │
└─────────────────────────────────────────────────────────┘
```

### Domínios de Negócio

| Domínio | Descrição |
|---|---|
| **Artigos Científicos** | Agregação, parsing, classificação e distribuição de artigos de Análise do Comportamento (ABA, RFT) |
| **Feeds RSS/Atom** | Sincronização periódica de múltiplas fontes acadêmicas com deduplicação |
| **Categorização Inteligente** | Classificação automática multi-categoria usando LLMs e sentence-transformers |
| **Busca Full-Text** | Motor de busca FTS5 com sugestões e fallback LIKE |
| **Analytics** | Tracking de pageviews e eventos com anonimização de IP (LGPD) |
| **Open Graph** | Geração dinâmica de metadados e imagens OG para compartilhamento social |
| **Processamento PDF** | Upload, extração de metadados e texto com PyMuPDF/pdfplumber |

---

## 2. Estrutura de Diretórios

```
bhub-backend-python/
├── app/
│   ├── main.py                    # Entry point + lifespan (353 linhas)
│   ├── config.py                  # pydantic-settings (191 linhas)
│   ├── database.py                # SQLAlchemy async + FTS5 setup (144 linhas)
│   ├── api/                       # Camada REST
│   │   ├── __init__.py            # Agrega routers
│   │   ├── deps.py                # Dependências compartilhadas
│   │   ├── auth/                  # Login, refresh, logout, register
│   │   └── v1/                    # API versionada
│   │       ├── articles.py        # Listagem pública, detalhe, similares, download
│   │       ├── categories.py      # CRUD de categorias
│   │       ├── authors.py         # Listagem de autores
│   │       ├── feeds.py           # Listagem de feeds
│   │       ├── search.py          # Busca full-text
│   │       ├── ai.py              # Classificação e tradução por IA
│   │       ├── analytics.py       # Eventos de analytics
│   │       ├── banners.py         # Banners
│   │       ├── opengraph.py       # Metadados Open Graph
│   │       ├── contact.py         # Formulário de contato
│   │       ├── csrf.py            # Token CSRF
│   │       └── admin/             # CRUD administrativo
│   │           ├── articles.py    # Gerenciamento de artigos (424 linhas)
│   │           ├── feeds.py       # Gerenciamento de feeds (204 linhas)
│   │           ├── stats.py       # Estatísticas do sistema
│   │           └── analytics.py   # Dados analíticos
│   ├── web/                       # Camada SSR + HTMX
│   │   ├── router.py              # Agrega rotas web
│   │   ├── routes.py              # Páginas públicas (690 linhas)
│   │   ├── auth.py                # Login/logout SSR com cookies
│   │   ├── admin.py               # Dashboard administrativo
│   │   ├── translation.py         # Tradução on-demand via HTMX
│   │   └── templating.py          # Setup Jinja2 + filtros customizados
│   ├── core/                      # Cross-cutting concerns
│   │   ├── security.py            # JWT + fastapi-users (109 linhas)
│   │   ├── refresh_token.py       # Refresh tokens com rotação (320 linhas)
│   │   ├── csrf.py                # Duplo-submit cookie pattern (146 linhas)
│   │   ├── csrf_middleware.py     # Middleware CSRF
│   │   ├── auth_cookie_middleware.py     # HttpOnly cookie handler (87 linhas)
│   │   ├── access_token_cookie_middleware.py  # Cookie-to-header bridge (30 linhas)
│   │   ├── analytics_middleware.py # Auto-tracking pageviews (170 linhas)
│   │   ├── security_headers.py    # HSTS, CSP, X-Frame-Options (110 linhas)
│   │   ├── limiter.py             # Rate limiter via slowapi
│   │   ├── rate_limiting.py       # Configuração de limites
│   │   ├── logging.py             # Loguru setup (124 linhas)
│   │   ├── log_sanitizer.py       # Sanitização de PII nos logs
│   │   ├── alerting.py            # Alertas via webhook
│   │   ├── ip_anonymization.py    # Anonimização LGPD
│   │   ├── scheduler_lock.py      # Lock distribuído para jobs (188 linhas)
│   │   └── exceptions.py          # Handlers de exceção customizados
│   ├── models/                    # ORM — 15 modelos
│   │   ├── base.py                # TimestampMixin (created_at/updated_at)
│   │   ├── user.py                # Usuários (fastapi-users + extras)
│   │   ├── article.py             # Artigo — domínio central (160 linhas)
│   │   ├── author.py              # Autores com ORCID
│   │   ├── category.py            # Categorias + DEFAULT_CATEGORIES
│   │   ├── feed.py                # Fontes RSS/Atom (131 linhas)
│   │   ├── banner.py              # Banners
│   │   ├── contact.py             # Mensagens de contato
│   │   ├── pdf_metadata.py        # Metadados de PDF
│   │   ├── article_category.py    # M2M Article↔Category
│   │   ├── analytics.py           # Events, Sessions, Metrics
│   │   ├── scheduler_lock.py      # Lock para jobs
│   │   ├── refresh_token.py       # Refresh tokens
│   │   └── translation_cache.py   # Cache de traduções
│   ├── schemas/                   # Pydantic — I/O da API
│   ├── services/                  # Lógica de negócio — 11 serviços
│   │   ├── feed_aggregator.py     # Orquestração de sync (376 linhas)
│   │   ├── article_parser.py      # Parse de entradas RSS (535 linhas)
│   │   ├── web_scraper.py         # Scraping web como fallback (477 linhas)
│   │   ├── search_service.py      # FTS5 + sugestões (280 linhas)
│   │   ├── classification_service.py  # Classificação multi-categoria (206 linhas)
│   │   ├── background_tasks.py    # Tarefas assíncronas (220 linhas)
│   │   ├── pdf_service.py         # Processamento PDF (453 linhas)
│   │   ├── opengraph_service.py   # OG metadata + imagens (349 linhas)
│   │   ├── analytics_service.py   # Sessões e eventos
│   │   └── translation_cache_service.py
│   ├── ai/                        # Abstração multi-provedor IA
│   │   ├── manager.py             # Orquestrador com fallback (446 linhas)
│   │   ├── local_llm_service.py   # llama.cpp local
│   │   └── model_manager.py       # Download/gestão de modelos
│   ├── ml/                        # Machine Learning
│   │   ├── embedding_classifier.py   # Sentence-transformers (305 linhas)
│   │   └── impact_rating.py          # Impact scoring 1-10 (169 linhas)
│   ├── jobs/                      # Tarefas agendadas
│   │   └── scheduler.py           # APScheduler config (108 linhas)
│   └── templates/                 # Jinja2 — 17 templates SSR
├── alembic/                       # Migrações (7 versões)
├── tests/                         # 25 arquivos de teste
├── scripts/vps/                   # Deploy, backup, health-check
├── config/nginx/, config/pm2/
├── pyproject.toml                 # Build (hatchling), deps, ruff, mypy, pytest
├── requirements.txt
├── Dockerfile                     # 47 linhas
└── docker-compose.yml
```

---

## 3. Pontos Fortes (Strengths)

### 3.1 Modularidade com Limites de Domínio Bem Definidos

Cada camada tem responsabilidade única:
- `api/` — transporte HTTP, roteamento, status codes
- `services/` — regras de negócio puras, independentes de framework
- `models/` — persistência, sem expor SQL bruto nas rotas
- `core/` — preocupações transversais sem vazamento para negócio

### 3.2 Estratégia de Segurança Robusta (Defesa em Profundidade)

A stack de middlewares aplica **6 camadas** de proteção na ordem correta:

| Ordem | Middleware | Função |
|---|---|---|
| 1 | `SecurityHeadersMiddleware` | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, remove Server/X-Powered-By |
| 2 | `CSRFMiddleware` | Double-submit cookie pattern com validação por dependência |
| 3 | `AuthCookieMiddleware` | HttpOnly `access_token` cookie para SSR |
| 4 | `AccessTokenCookieMiddleware` | Bridge cookie→header para compatibilidade fastapi-users |
| 5 | `AnalyticsMiddleware` | Auto-tracking pageviews, respeita DNT, anonimiza IP |
| 6 | `CORSMiddleware` | Dev: regex para redes locais; Prod: allowlist explícita |

Destaques adicionais:
- **Refresh token com rotação**: cada refresh revoga o token anterior e emite novo (`core/refresh_token.py:238-243`)
- **Validação de produção forçada**: `SECRET_KEY >= 32 chars`, `DEBUG=False`, `ALLOWED_ORIGINS` sem wildcards — validado via `model_validator` no `config.py:170-182`
- **Rate limiting granular**: global 100/min, cron 3/hora, AI 100/dia
- **Sanitização de logs**: PII e credenciais nunca vazam para logs

### 3.3 Orquestração Inteligente de IA com Fallback

O `AIManager` (`app/ai/manager.py`, 446 linhas) implementa cadeia de fallback automática:

```
DeepSeek API (deepseek-chat + JSON structured output)
  ↓ falha
Local LLM (llama.cpp — Phi-3-mini)
  ↓ falha
OpenRouter (Claude 3 Haiku)
  ↓ falha
HuggingFace (bart-large-mnli, opus-mt-en-pt)
  ↓ falha
Embedding Classifier local (sentence-transformers)
```

Cada provedor implementa a interface `classify(text) → (slug, confidence)` e `translate(text, lang) → text`.

### 3.4 Controle Distribuído de Concorrência

`app/core/scheduler_lock.py` (188 linhas) implementa lock baseado em banco com:
- Acquisição atômica com `INSERT OR IGNORE`
- Heartbeat para renovação automática
- Expiração para recuperação de locks órfãos
- Suporte a 3 modos: `"app"` (embedded), `"worker"` (processo separado), `"off"` (cron externo)

### 3.5 Progressive Enhancement com HTMX

O sistema serve simultaneamente:
- **REST API JSON** para SPAs/mobile (`/api/v1/*`)
- **SSR com HTMX** para admin e páginas públicas (`/`, `/admin`, `/articles/{id}`)

Isso elimina a necessidade de um frontend SPA separado para o admin, reduzindo complexidade operacional.

### 3.6 Qualidade de Código e Ferramentas

| Ferramenta | Configuração |
|---|---|
| **Ruff** | py312, 100 chars, isort integrado, regras E/W/F/I/B/C4/UP/ARG/SIM |
| **Mypy** | strict mode (`strict = true`) |
| **Pytest** | `asyncio_mode = "auto"`, 25 arquivos de teste |
| **Pre-commit** | configurado para dev |
| **Alembic** | 7 migrações versionadas |

---

## 4. Débitos Técnicos e Pontos de Atenção (Weaknesses)

### 4.1 Gerenciamento Frágil de Tarefas Assíncronas [CRÍTICO]

**Local:** `app/services/background_tasks.py` e callers

Tarefas pesadas (classificação paralela de artigos, download de PDFs) são disparadas via `asyncio.create_task()`. Isso implica:

- **Perda de trabalho em restart**: se o processo cair, todas as tasks em andamento são perdidas sem retry
- **Sem políticas de retry**: falhas transitórias em APIs externas (DeepSeek, HuggingFace) não são tratadas automaticamente
- **Sem observabilidade**: não há métricas de fila, tempo de espera ou taxa de falha
- **Sem backpressure**: picos de sync podem disparar tasks ilimitadas, esgotando conexões

### 4.2 Ausência de Injeção de Dependências [ALTO]

A maioria dos serviços é instanciada diretamente nos módulos que os consomem (`ServiceClass()` no top-level), em vez de usar o sistema `Depends()` do FastAPI. Consequências:

- **Testabilidade reduzida**: mocking depende de monkey-patching em vez de substituição de dependências
- **Acoplamento rígido**: serviços dependem diretamente de implementações concretas, não de interfaces
- **Dificuldade de evolução**: trocar uma implementação (ex: SQLite → PostgreSQL) exige alterar múltiplos arquivos

### 4.3 Gargalo de Concorrência — SQLite [MÉDIO-ALTO]

A aplicação usa SQLite com WAL mode, o que é adequado para estágios iniciais. Porém:

- **Escrita single-writer**: o lock de escrita do SQLite torna-se gargalo com ingestão de feeds, tracking de analytics, e múltiplos leitores simultâneos
- **FTS5 vs TSVector**: a busca full-text com FTS5 é funcional, mas PostgreSQL oferece `pg_trgm` + `TSVector` com ranking muito superior para buscas acadêmicas multilíngues
- **Sem conexões concorrentes reais**: o modelo async do aiosqlite é limitado pelo design fundamental do SQLite

### 4.4 Observabilidade Limitada [MÉDIO]

Faltam métricas de aplicação para:
- Latência e taxa de erro dos provedores de IA (DeepSeek, OpenRouter)
- Tempo de processamento do pipeline de sync
- Taxa de acerto/erro do classificador
- Consumo de memória dos modelos ML carregados

### 4.5 Artefatos Residuais [BAIXO]

Presença de diretório literal `{api/` na árvore do projeto — resquício de expansão incorreta de chaves no shell durante criação de diretórios.

---

## 5. Plano de Ação Recomendado (Priorizado)

### Fase 1 — Estabilização (Semanas 1-2)

- [ ] **1.1 Implementar Fila de Tarefas Persistente**
  - Migrar `asyncio.create_task()` para **ARQ** (async/await nativo sobre Redis) ou **Celery**
  - Adicionar retry com backoff exponencial para falhas em APIs externas
  - Expor métricas de fila (tamanho, latência, taxa de falha)

- [ ] **1.2 Refatorar Injeção de Dependências**
  - Converter serviços para usar `fastapi.Depends()` como fábrica
  - Criar protocolos/interfaces para os serviços principais (`ArticleParser`, `FeedAggregator`, `AIManager`)
  - Garantir que todo teste possa substituir dependências sem monkey-patching

### Fase 2 — Escalonamento (Semanas 3-4)

- [ ] **2.1 Migrar Banco de Dados para PostgreSQL**
  - Atualizar `DATABASE_URL` e driver (`asyncpg`)
  - Migrar FTS5 → `TSVector` + `pg_trgm` para busca multilíngue com ranking
  - Manter WAL/WAL2 para performance
  - Atualizar Alembic migrations

- [ ] **2.2 Instituir Observabilidade (APM)**
  - Instrumentar com **OpenTelemetry** (traces + métricas)
  - Adicionar dashboard **Grafana** para métricas de IA (latência por provedor, fallback rate)
  - Configurar alertas para degradação dos provedores de IA

### Fase 3 — Robustez (Semanas 5-6)

- [ ] **3.1 Limpeza de Infraestrutura**
  - Remover diretório `{api/` e validar que não há referências
  - Auditar `.gitignore` para artefatos de build/venv

- [ ] **3.2 Expandir Cobertura de Testes**
  - Testes de integração para fluxo completo: sync → parse → classify → serve
  - Testes de contrato para API pública (OpenAPI schema validation)
  - Testes de resiliência para cenários de falha dos provedores IA

---

## 6. Resumo das Métricas

| Métrica | Valor |
|---|---|
| Total de arquivos Python | 144 |
| Linhas de código (aprox.) | ~18.800 |
| Modelos ORM | 15 |
| Serviços de negócio | 11 |
| Middlewares | 6 |
| Migrações Alembic | 7 |
| Arquivos de teste | 25 |
| Endpoints REST (estimado) | 60+ |
| Python mínimo | 3.12 |
| Build system | Hatchling |
| ORM | SQLAlchemy 2.0+ async |
| Autenticação | fastapi-users + JWT + refresh tokens rotativos |
| CSRF | Double-submit cookie pattern |
| Rate Limiting | slowapi |
| Logging | Loguru com sanitização PII |
| Scheduling | APScheduler com lock distribuído |
| AI Providers | 4 (DeepSeek, Local LLM, OpenRouter, HuggingFace) |
| ML Models | Sentence-transformers + impact scoring |
| Frontend | REST API + SSR com HTMX + Jinja2 |
| Deploy | Docker + docker-compose + PM2 + Nginx |

---

## 7. Diagrama de Fluxo — Sincronização de Feeds

```
Cron/Scheduler (/api/v1/cron/sync)
  │
  ▼
FeedAggregatorService.sync_feed(feed_url)
  │
  ├─► fetch_feed() ── httpx/aiohttp ──► XML/RSS cru
  ├─► ArticleParserService.parse_entry(entry)
  │     ├─► extrai título, abstract, DOI, autores, URLs, PDF/images
  │     ├─► detecta Open Access (is_open_access)
  │     └─► retorna ArticleCreate schema
  ├─► deduplica (DOI hash, título similarity)
  ├─► persiste Article + Authors + PDFMetadata
  │
  ▼
BackgroundTasks.dispatch()
  │
  ├─► asyncio.create_task(ClassificationService.classify(article))  ⚠️ sem fila
  │     └─► AIManager.classify(text)
  │           ├─► 1. DeepSeek API
  │           ├─► 2. Local LLM (llama.cpp)
  │           ├─► 3. OpenRouter (Claude)
  │           ├─► 4. HuggingFace (bart-large-mnli)
  │           └─► 5. Embedding Classifier (local)
  │
  └─► asyncio.create_task(BackgroundTasks.download_pdf(article))   ⚠️ sem fila
```

---

## 8. Diagrama de Middlewares (Ordem de Execução)

```
Request
  │
  ▼
SecurityHeadersMiddleware     → adiciona headers de segurança
  │
  ▼
CSRFMiddleware                → gera token CSRF (GET), valida (POST/PUT/DELETE)
  │
  ▼
AuthCookieMiddleware          → intercepta login, seta cookie HttpOnly
  │
  ▼
AccessTokenCookieMiddleware   → cookie → header Authorization: Bearer
  │
  ▼
AnalyticsMiddleware           → track pageview, anonimiza IP, respeita DNT
  │
  ▼
CORSMiddleware                → valida Origin contra allowlist
  │
  ▼
Route Handler (API ou SSR)
```

---

## 9. Conclusão

O backend do BHub apresenta uma arquitetura **sólida para o estágio atual do produto**, com decisões arquiteturais maduras em segurança (CSRF, refresh token rotation, rate limiting) e integração com IA (multi-provider com fallback). A separação de camadas é limpa e o uso de SSR+HTMX como alternativa ao SPA é pragmático.

Os **3 débitos principais** que limitam a escalabilidade são:

1. **Tarefas assíncronas sem fila** — risco de perda de trabalho e ausência de retry (resolver com ARQ/Celery)
2. **Injeção de dependências manual** — dificulta testes e evolução (resolver com `Depends()` e interfaces)
3. **SQLite como gargalo** — single-writer limita concorrência (resolver com PostgreSQL + TSVector)

O plano de ação recomendado prioriza a estabilização (fila + DI) antes do escalonamento (PostgreSQL + observabilidade), seguindo a ordem natural de maturidade do sistema.
