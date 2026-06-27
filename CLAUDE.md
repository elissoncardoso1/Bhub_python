# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BHUB is a scientific article aggregation platform specializing in Behavior Analysis (ABA/RFT) research. The backend is a FastAPI async Python app that aggregates RSS feeds, classifies articles with ML, provides full-text search, and renders an SSR web UI via Jinja2/HTMX.

The main application lives in `bhub-backend-python/`. All commands below assume you're working inside that directory unless stated otherwise.

---

## Commands

### Setup
```bash
cd bhub-backend-python
pip install -r requirements-dev.txt
cp .env.example .env           # then edit .env
alembic upgrade head
python scripts/create_superuser.py
```

### Run (Development)
```bash
uvicorn app.main:app --reload
```

### Run (Docker)
```bash
docker-compose up -d
```

### Tests
```bash
pytest tests/ -v
pytest tests/test_smoke.py -v          # single file
pytest tests/ -v --cov=app --cov-report=html
```

### Lint & Type Check
```bash
ruff check app/
ruff check --fix app/
mypy app/
```

### Database Migrations
```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1
```

### Utility Scripts
```bash
python scripts/seed_feeds.py           # populate default RSS feeds
python scripts/sync_feeds.py           # manual feed sync
python scripts/reclassify_articles.py  # batch ML reclassification
python scripts/setup_local_llm.py      # download Phi-3-mini model
python scripts/backup_db.py
```

---

## Architecture

### Layer Diagram

```
Client (HTML/HTMX/Tailwind)
        ↓
Middlewares: CSRF, Auth cookies, Analytics, Rate limiting, Security headers
        ↓
┌──────────────────────────────────┐
│  app/api/v1/       REST API      │  JSON responses for SPA/HTMX
│  app/web/          SSR Routes    │  Jinja2 HTML rendering
└──────────────────────────────────┘
        ↓
app/services/        Business logic layer
        ↓
app/models/          SQLAlchemy 2.0 async ORM
        ↓
SQLite (dev) / PostgreSQL (prod) + Redis (ARQ job queue)
```

### Key Modules

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app factory, lifespan, middleware registration |
| `app/config.py` | Pydantic settings (reads `.env`) |
| `app/database.py` | Async SQLAlchemy engine + FTS5 setup |
| `app/api/deps.py` | Shared FastAPI `Depends()` (DB session, current user) |
| `app/core/security.py` | JWT + fastapi-users integration |
| `app/core/csrf.py` + `csrf_middleware.py` | Double-submit cookie CSRF |
| `app/core/ip_anonymization.py` | LGPD-compliant IP hashing |
| `app/services/feed_aggregator.py` | RSS ingestion + deduplication |
| `app/services/classification_service.py` | sentence-transformers classifier |
| `app/services/search_service.py` | FTS5 + LIKE fallback |
| `app/ai/manager.py` | Multi-provider LLM (DeepSeek → OpenRouter → local llama.cpp) |
| `app/ml/embedding_classifier.py` | sentence-transformers wrapper |
| `app/jobs/scheduler.py` | APScheduler periodic jobs |
| `app/services/task_dispatcher.py` | ARQ/Redis async job queue |
| `app/web/templating.py` | Jinja2 environment + custom filters |
| `app/web/routes.py` | Public SSR routes (home, articles, categories, about, contact) |
| `app/web/admin.py` | Admin SSR routes (`/admin` dashboard, `/admin/analytics`) |
| `app/services/analytics_service.py` | Traffic / content / events / time-series stats |
| `app/static/css/design-tokens.css` | **Design system v3 tokens** (warm burgundy/sage palette) — source of truth |
| `app/static/css/fonts.css` + `app/static/fonts/` | Self-hosted variable fonts (Reddit Sans · Chivo Mono · Elms Sans) |
| `tailwind.config.js` | Tailwind colors/fonts remapped to the v3 palette (compiles to `static/css/output.css`) |

### Article Ingestion Flow
1. APScheduler triggers feed sync (hourly)
2. `FeedAggregator` fetches RSS → `feedparser` parses entries
3. `ArticleParser` extracts title, DOI, abstract, authors
4. `WebScraper` fetches full text; `PDFService` handles PDFs
5. `ClassificationService` assigns up to 3 behavior-analysis categories
6. `ImpactRating` scores relevance; article written to DB + FTS5 index

### Authentication
- **JWT** access tokens stored as `HttpOnly` cookies via `access_token_cookie_middleware.py`
- Refresh token rotation in `app/core/refresh_token.py` (stored in DB, `app/models/refresh_token.py`)
- CSRF protection: double-submit cookie pattern; state-changing API routes require `X-CSRF-Token` header

### AI/LLM Strategy
- Provider priority: DeepSeek → OpenRouter → local Phi-3-mini (llama.cpp)
- `app/ai/manager.py` handles selection, retries, fallback
- `app/ai/local_llm_service.py` wraps llama.cpp (optional, enabled via env)
- ML classification can run offline using `sentence-transformers` (no API key needed)

### Frontend / Design System (v3 — warm burgundy/sage)

- SSR via Jinja2 + HTMX; styling via Tailwind compiled locally to `app/static/css/output.css`
- **Tokens are the source of truth** — `design-tokens.css` (CSS variables) + `tailwind.config.js` (utility scales). Reference tokens/utilities; don't hardcode hex. Tailwind's `slate-*` is remapped to warm stone, so legacy `slate-*` warms up automatically.
- Brand palette: burgundy `#58272d` (primary), sage `#a3a16e`, tan `#a48c68`, cream `#f0eebd`, paper `#f4f0f1`. See `docs/ui-ux/PALETA_CORES.md`.
- Fonts are **self-hosted** (no Google Fonts CDN): Reddit Sans (UI), Chivo Mono (code), Elms Sans (`font-data`, metrics) — variable woff2 under `app/static/fonts/` (OFL, committed)
- **Recompile after template/CSS class changes:** `npx tailwindcss@3.4.0 -i ./app/static/css/input.css -o ./app/static/css/output.css --minify`
- Admin (`/admin`, `/admin/analytics`) and public pages both use the v3 system; the legacy `app.css` (`.panel/.btn/.toast-item`) remains only for the JS toast runtime

---

## Configuration

Key `.env` variables:
```
SECRET_KEY          # JWT signing key (≥32 chars in production)
DATABASE_URL        # aiosqlite:///./bhub.db  OR  postgresql+asyncpg://...
REDIS_URL           # redis://localhost:6379/0
ENVIRONMENT         # dev | staging | production
DEBUG               # false in production
ALLOWED_ORIGINS     # comma-separated CORS whitelist
ENABLE_SCHEDULER    # true to enable APScheduler jobs
DEEPSEEK_API_KEY    # primary LLM provider
OPENROUTER_API_KEY  # fallback LLM provider
```

---

## Known Technical Debt

From `BHUB_REFACTORING_PLAN.md`:
1. **Background Tasks** — Some tasks bypass ARQ and use `BackgroundTasks` directly; migrate to `task_dispatcher.py`
2. **Dependency Injection** — Several services are manually instantiated; the plan is to use `Depends()` + Protocol interfaces (`app/interfaces/`)
3. **SQLite in Production** — dev uses SQLite FTS5; migration `008_postgres_fts` adds a PostgreSQL `TSVECTOR` `search_vector` (+ trigger, GIN/pg_trgm indexes) and a plain `search_vector` column on SQLite. Production search scale → PostgreSQL.

---

## Gotchas

- **`search_vector` "no such column" on `/articles`** — the DB is behind on migrations. The `Article.search_vector` column is `deferred=True`, but that is **not** honored when the entity is wrapped in `.subquery()` (e.g. the count query), so the column is selected and a stale DB 500s. Fix: `alembic upgrade head`. If `alembic_version` is out of sync with the actual schema (tables from later revisions already present), `stamp` to the right revision first, then upgrade.
- **Tailwind output is committed** — after editing template classes or CSS, recompile `output.css` (see Frontend / Design System) or new utilities won't exist at runtime.

---

## Documentation

Full docs live in `docs/` — start at [`docs/README.md`](docs/README.md) (indexed by Arquitetura / Configuração / Deploy / Segurança / UI-UX / Implementação / Refatoração). Design system: `docs/ui-ux/PALETA_CORES.md` + the in-code tokens.

---

## Testing Notes

- Tests live in `tests/` with async support via `pytest-asyncio`
- `tests/conftest.py` provides fixtures (in-memory SQLite, test client)
- Use `pytest -x` to stop on first failure during development
- Smoke tests in `tests/test_smoke.py` cover critical API paths

---

## Code Style

- **Linter**: ruff, 100-char line length, strict ruleset (configured in `pyproject.toml`)
- **Types**: mypy strict mode — all public functions must have type annotations
- **Async**: all DB calls, HTTP requests, and service methods must be `async def`
- **Models**: SQLAlchemy 2.0 style (`Mapped[T]`, `mapped_column`)
