# Plano de Refatoração — BHub Backend (Python)

**Baseado em:** ARCHITECTURE_REPORT.md (06/mai/2026) + Bhub_Backend_Architecture_Review.md (Obsidian) + Python Wiki (OOP, ABC, Protocolos)  
**Versão:** 1.0 — Elisson Coimbra, CRP 22/01992 / pontobhv

---

## Sumário Executivo

O BHub Backend apresenta três débitos técnicos críticos identificados de forma convergente tanto no relatório de análise atualizado quanto no review armazenado no Obsidian. Este plano traduz as recomendações em código concreto, usando os padrões Python documentados na Python Wiki (ABC, Protocolos via `typing.Protocol`, duck typing).

| Débito | Severidade | Arquivo(s) Alvo |
|--------|-----------|-----------------|
| Tarefas assíncronas sem fila | CRÍTICO | `app/services/background_tasks.py` |
| Injeção de Dependências manual | ALTO | `app/api/deps.py` + todos os serviços |
| SQLite como gargalo de escrita | MÉDIO-ALTO | `app/database.py` + `app/core/search_service.py` |

---

## Fase 1 — Injeção de Dependências com `Protocol` + `Depends()`

### Contexto (Python Wiki — `oop/heranca-e-polimorfismo.md`)

O vault documenta dois padrões aplicáveis aqui:
- **ABC (`abstractmethod`)** — garante contrato de interface em tempo de definição
- **`typing.Protocol`** — duck typing estrutural, sem herança forçada (preferido para DI em FastAPI)

### Problema Atual

```python
# app/api/v1/articles.py  ← PADRÃO ATUAL (problemático)
from app.services.classification_service import ClassificationService
from app.services.search_service import SearchService

_classifier = ClassificationService()   # instância global no top-level
_search = SearchService()               # impossível mockar sem monkey-patch
```

### Refatoração: Protocolos + `Depends()`

**Passo 1 — Criar interfaces via `Protocol` em `app/interfaces/`**

```python
# app/interfaces/services.py  ← NOVO ARQUIVO
from typing import Protocol, runtime_checkable
from app.schemas.article import ArticleCreate, ArticleOut, CategorySlug

@runtime_checkable
class IClassificationService(Protocol):
    async def classify(self, text: str) -> tuple[CategorySlug, float]:
        """Retorna (slug_categoria, confiança 0–1)."""
        ...

    async def classify_batch(
        self, texts: list[str]
    ) -> list[tuple[CategorySlug, float]]:
        ...

@runtime_checkable
class ISearchService(Protocol):
    async def search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[ArticleOut]:
        ...

    async def suggest(self, prefix: str) -> list[str]:
        ...

@runtime_checkable
class IFeedAggregator(Protocol):
    async def sync_feed(self, feed_url: str) -> int:
        """Retorna número de artigos novos ingeridos."""
        ...

    async def sync_all(self) -> dict[str, int]:
        ...

@runtime_checkable
class IAIManager(Protocol):
    async def classify(self, text: str) -> tuple[CategorySlug, float]:
        ...

    async def translate(self, text: str, target_lang: str) -> str:
        ...

    async def is_available(self) -> bool:
        ...
```

**Passo 2 — Fábricas assíncronas em `app/api/deps.py`**

```python
# app/api/deps.py  ← SUBSTITUIÇÃO COMPLETA
from typing import Annotated, AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.interfaces.services import (
    IClassificationService, ISearchService,
    IFeedAggregator, IAIManager,
)

# ── Sessão de banco ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

DbSession = Annotated[AsyncSession, Depends(get_db)]

# ── Serviços ─────────────────────────────────────────────────────────────────

def get_classification_service(
    db: DbSession,
) -> IClassificationService:
    from app.services.classification_service import ClassificationService
    return ClassificationService(db=db)

def get_search_service(db: DbSession) -> ISearchService:
    from app.services.search_service import SearchService
    return SearchService(db=db)

def get_ai_manager() -> IAIManager:
    from app.ai.manager import AIManager
    return AIManager()

def get_feed_aggregator(
    db: DbSession,
    ai: Annotated[IAIManager, Depends(get_ai_manager)],
) -> IFeedAggregator:
    from app.services.feed_aggregator import FeedAggregatorService
    return FeedAggregatorService(db=db, ai_manager=ai)

# Aliases Annotated para uso nas rotas
ClassifierDep = Annotated[IClassificationService, Depends(get_classification_service)]
SearchDep      = Annotated[ISearchService, Depends(get_search_service)]
AIDep          = Annotated[IAIManager, Depends(get_ai_manager)]
FeedAggDep     = Annotated[IFeedAggregator, Depends(get_feed_aggregator)]
```

**Passo 3 — Uso nas rotas (antes × depois)**

```python
# ANTES — app/api/v1/articles.py
_search = SearchService()

@router.get("/articles")
async def list_articles(q: str | None = None):
    if q:
        return await _search.search(q)  # impossível substituir no teste

# DEPOIS — app/api/v1/articles.py
from app.api.deps import SearchDep

@router.get("/articles")
async def list_articles(
    q: str | None = None,
    search: SearchDep = ...,          # FastAPI injeta automaticamente
):
    if q:
        return await search.search(q)
```

**Passo 4 — Serviços recebem dependências no `__init__`**

```python
# app/services/classification_service.py  ← REFATORADO
from sqlalchemy.ext.asyncio import AsyncSession
from app.interfaces.services import IAIManager

class ClassificationService:
    """Recebe dependências via injeção — sem estado global."""

    def __init__(self, db: AsyncSession, ai_manager: IAIManager | None = None):
        self._db = db
        self._ai = ai_manager  # None → usa classificador local (embedding)

    async def classify(self, text: str) -> tuple[str, float]:
        if self._ai and await self._ai.is_available():
            return await self._ai.classify(text)
        return await self._local_classify(text)

    async def _local_classify(self, text: str) -> tuple[str, float]:
        from app.ml.embedding_classifier import EmbeddingClassifier
        clf = EmbeddingClassifier()
        return await clf.predict(text)
```

**Testes — como fica depois da refatoração**

```python
# tests/test_articles.py  ← SEM MONKEY-PATCH
import pytest
from httpx import AsyncClient
from app.interfaces.services import ISearchService

class FakeSearchService:
    """Stub mínimo que satisfaz o Protocol."""
    async def search(self, query: str, **_) -> list:
        return [{"id": 1, "title": f"Resultado para {query}"}]
    async def suggest(self, prefix: str) -> list[str]:
        return [prefix + "_sugerido"]

@pytest.fixture
def override_search(app):
    from app.api.deps import get_search_service
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    yield
    app.dependency_overrides.clear()

async def test_search_returns_results(client: AsyncClient, override_search):
    resp = await client.get("/api/v1/articles?q=ABA")
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Resultado para ABA"
```

---

## Fase 2 — Fila de Tarefas Persistente com ARQ

### Problema Atual

```python
# app/services/background_tasks.py  ← PADRÃO ATUAL
async def dispatch_post_ingest(article_id: int) -> None:
    asyncio.create_task(                     # ⚠ task morrerá com o processo
        ClassificationService().classify_article(article_id)
    )
    asyncio.create_task(                     # ⚠ sem retry, sem observabilidade
        PdfService().download_pdf(article_id)
    )
```

### Por que ARQ (não Celery)

| Critério | ARQ | Celery |
|----------|-----|--------|
| async/await nativo | ✅ | ❌ (threading model) |
| Overhead de infra | Redis (já comum) | Redis + Broker config complexo |
| Integração FastAPI | `Depends()` direto | Workarounds necessários |
| Retry com backoff | `retry=3, defer_by=...` | `max_retries`, `countdown` |
| Tamanho do código | ~80 linhas | ~300+ linhas de config |

### Implementação ARQ

**Instalação**

```bash
# pyproject.toml — adicionar ao [project.dependencies]
"arq>=0.26.1",
"redis[hiredis]>=5.0",
```

**Definição das tarefas**

```python
# app/jobs/tasks.py  ← NOVO ARQUIVO
from __future__ import annotations
import logging
from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Tarefas ARQ ──────────────────────────────────────────────────────────────

async def task_classify_article(
    ctx: dict,
    article_id: int,
) -> dict:
    """Classifica artigo com fallback multi-provedor. Retry automático."""
    db: AsyncSession = ctx["db"]
    from app.services.classification_service import ClassificationService
    from app.ai.manager import AIManager

    service = ClassificationService(db=db, ai_manager=AIManager())
    result = await service.classify_article(article_id)
    logger.info("Artigo %d classificado: %s (%.2f)", article_id, *result)
    return {"article_id": article_id, "category": result[0], "confidence": result[1]}


async def task_download_pdf(
    ctx: dict,
    article_id: int,
    pdf_url: str,
) -> dict:
    """Download e extração de metadados PDF. Retry automático."""
    db: AsyncSession = ctx["db"]
    from app.services.pdf_service import PdfService

    service = PdfService(db=db)
    metadata = await service.download_and_extract(article_id, pdf_url)
    return {"article_id": article_id, "pages": metadata.get("pages")}


# ── Configuração do Worker ────────────────────────────────────────────────────

async def startup(ctx: dict) -> None:
    """Contexto compartilhado entre tasks (conexão de banco, etc.)."""
    from app.database import async_session_maker
    ctx["session_factory"] = async_session_maker
    # Cria sessão por task em on_job_start (ver abaixo)

async def shutdown(ctx: dict) -> None:
    pass

async def on_job_start(ctx: dict) -> None:
    """Abre sessão de banco exclusiva para cada job."""
    from app.database import async_session_maker
    session = async_session_maker()
    await session.__aenter__()
    ctx["db"] = session

async def on_job_end(ctx: dict) -> None:
    """Fecha sessão ao término do job (commit ou rollback)."""
    session: AsyncSession = ctx.get("db")
    if session:
        await session.__aexit__(None, None, None)


class WorkerSettings:
    """Configuração central do worker ARQ."""
    functions = [task_classify_article, task_download_pdf]
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end
    max_jobs = 10
    job_timeout = 300        # 5 min por job
    max_tries = 3            # retry automático
    retry_jobs = True
    keep_result = 86_400     # mantém resultado por 24h
    health_check_interval = 30

    @classmethod
    def redis_settings(cls):
        from arq.connections import RedisSettings
        from app.config import settings
        return RedisSettings.from_dsn(settings.REDIS_URL)
```

**Dispatcher — substitui `background_tasks.py`**

```python
# app/services/task_dispatcher.py  ← SUBSTITUI background_tasks.py
from arq import ArqRedis
from arq.connections import create_pool, RedisSettings

_arq_pool: ArqRedis | None = None

async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        from app.config import settings
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


async def dispatch_classify_article(article_id: int) -> str:
    """Enfileira classificação. Retorna job_id para rastreamento."""
    pool = await get_arq_pool()
    job = await pool.enqueue_job(
        "task_classify_article",
        article_id,
        _defer_by=2,          # pequeno delay para deixar o persist concluir
    )
    return job.job_id


async def dispatch_download_pdf(article_id: int, pdf_url: str) -> str:
    pool = await get_arq_pool()
    job = await pool.enqueue_job(
        "task_download_pdf",
        article_id,
        pdf_url,
    )
    return job.job_id
```

**Integração no lifespan (`app/main.py`)**

```python
# app/main.py — dentro do lifespan (adicionar ao bloco existente)
from app.services.task_dispatcher import get_arq_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... inicializações existentes ...
    await get_arq_pool()          # pré-aquece pool Redis
    logger.info("ARQ pool conectado")
    yield
    # ... shutdown existente ...
```

**Execução do worker (docker-compose.yml)**

```yaml
# docker-compose.yml — adicionar serviço
  arq-worker:
    build: .
    command: arq app.jobs.tasks.WorkerSettings
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - db
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
```

**Antes × depois no ponto de dispatch**

```python
# ANTES — app/services/feed_aggregator.py
async def sync_feed(self, feed_url: str) -> int:
    articles = await self._parse_and_persist(feed_url)
    for art in articles:
        asyncio.create_task(self._classify(art.id))   # fogo e esquece
    return len(articles)

# DEPOIS
from app.services.task_dispatcher import dispatch_classify_article, dispatch_download_pdf

async def sync_feed(self, feed_url: str) -> int:
    articles = await self._parse_and_persist(feed_url)
    for art in articles:
        job_id = await dispatch_classify_article(art.id)
        logger.debug("Classificação enfileirada: job=%s artigo=%d", job_id, art.id)
        if art.pdf_url:
            await dispatch_download_pdf(art.id, art.pdf_url)
    return len(articles)
```

---

## Fase 3 — Migração SQLite → PostgreSQL

### Alterações em `app/database.py`

```python
# app/database.py  ← REFATORADO
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

# asyncpg para PostgreSQL (substituir aiosqlite)
engine = create_async_engine(
    settings.DATABASE_URL,          # postgresql+asyncpg://...
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,             # detecta conexões mortas
    pool_recycle=3600,
    echo=settings.DEBUG,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### Migração FTS5 → `TSVector` + `pg_trgm`

```python
# app/models/article.py  ← ADIÇÃO pós-migração

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy import event

class Article(Base, TimestampMixin):
    # ... campos existentes mantidos ...

    # Coluna TSVector (gerada automaticamente pelo trigger PostgreSQL)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        nullable=True,
        deferred=True,    # não carrega por padrão para economizar bandwidth
    )

    __table_args__ = (
        # Índice GIN para busca full-text
        Index(
            "idx_articles_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        # pg_trgm para busca por similaridade (sugestões, typos)
        Index(
            "idx_articles_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )
```

```sql
-- alembic/versions/008_fts_tsvector.sql  (novo arquivo de migração)

-- Extensão pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Coluna search_vector com weights por campo
ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

-- Função de atualização do vector
CREATE OR REPLACE FUNCTION articles_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('portuguese', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('portuguese', coalesce(NEW.abstract, '')), 'B') ||
        setweight(to_tsvector('english',    coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english',    coalesce(NEW.abstract, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger automático
CREATE TRIGGER articles_search_vector_trigger
    BEFORE INSERT OR UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION articles_search_vector_update();

-- Índice GIN para busca eficiente
CREATE INDEX IF NOT EXISTS idx_articles_search_vector
    ON articles USING GIN (search_vector);

-- Índice trgm para sugestões
CREATE INDEX IF NOT EXISTS idx_articles_title_trgm
    ON articles USING GIN (title gin_trgm_ops);
```

**`app/services/search_service.py` — usar TSVector**

```python
# app/services/search_service.py  ← SUBSTITUIÇÃO do bloco FTS5

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import to_tsquery

class SearchService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[ArticleOut]:
        # Normaliza query para tsquery (suporta português e inglês)
        ts_query = func.plainto_tsquery(
            text("'portuguese'"), query
        )

        stmt = (
            select(Article)
            .where(Article.search_vector.op("@@")(ts_query))
            .order_by(
                func.ts_rank_cd(Article.search_vector, ts_query).desc()
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return [ArticleOut.model_validate(a) for a in result.scalars()]

    async def suggest(self, prefix: str) -> list[str]:
        """Sugestões por similaridade trigrama (tolerante a typos)."""
        stmt = (
            select(Article.title)
            .where(Article.title.ilike(f"%{prefix}%"))
            .order_by(
                func.similarity(Article.title, prefix).desc()
            )
            .limit(5)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars())
```

---

## Fase 4 — Observabilidade (OpenTelemetry)

```python
# app/core/telemetry.py  ← NOVO ARQUIVO

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_telemetry(app_name: str = "bhub-backend") -> None:
    """Configura OpenTelemetry para traces + métricas."""

    # Traces
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())
    )
    trace.set_tracer_provider(tracer_provider)

    # Métricas customizadas para o domínio BHub
    meter = metrics.get_meter(app_name)

    # Instrumentação do AIManager
    global ai_latency, ai_fallback_counter
    ai_latency = meter.create_histogram(
        "ai.classify.duration_ms",
        description="Latência de classificação por provedor",
        unit="ms",
    )
    ai_fallback_counter = meter.create_counter(
        "ai.fallback.total",
        description="Total de fallbacks entre provedores de IA",
    )


# Uso no AIManager
class AIManager:
    async def classify(self, text: str) -> tuple[str, float]:
        import time
        for provider_name, provider in self._providers:
            start = time.monotonic()
            try:
                result = await provider.classify(text)
                ai_latency.record(
                    (time.monotonic() - start) * 1000,
                    {"provider": provider_name},
                )
                return result
            except Exception:
                ai_fallback_counter.add(1, {"from": provider_name})
                continue
        raise RuntimeError("Todos os provedores falharam")
```

---

## Limpeza de Infraestrutura

```bash
#!/usr/bin/env bash
# scripts/cleanup_artifacts.sh  ← NOVO

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

echo "→ Procurando diretório {api/ ..."
BROKEN_DIR="${REPO_ROOT}/{api"

if [ -d "$BROKEN_DIR" ]; then
    echo "  Encontrado: $BROKEN_DIR"
    # Verificar se há referências no código
    if grep -r '{api/' "${REPO_ROOT}/app" --include="*.py" -l 2>/dev/null; then
        echo "  ⚠ Referências encontradas — revisar antes de remover"
        exit 1
    fi
    rm -rf "$BROKEN_DIR"
    echo "  ✓ Removido"
else
    echo "  ✓ Não encontrado (já limpo)"
fi

# Verificar .gitignore
echo "→ Verificando .gitignore ..."
IGNORES=("__pycache__" "*.pyc" ".env" "venv/" ".venv/" "dist/" "*.egg-info/")
for pattern in "${IGNORES[@]}"; do
    if ! grep -qF "$pattern" "${REPO_ROOT}/.gitignore"; then
        echo "  FALTANDO: $pattern"
        echo "$pattern" >> "${REPO_ROOT}/.gitignore"
        echo "  ✓ Adicionado: $pattern"
    fi
done

echo "✓ Limpeza concluída"
```

---

## Checklist de Execução

### Fase 1 — Injeção de Dependências (Semanas 1–2)

- [ ] Criar `app/interfaces/services.py` com os `Protocol`s definidos acima
- [ ] Reescrever `app/api/deps.py` com fábricas e `Annotated` aliases
- [ ] Refatorar `ClassificationService.__init__` para receber `db` e `ai_manager`
- [ ] Refatorar `SearchService.__init__` para receber `db`
- [ ] Refatorar `FeedAggregatorService.__init__` para receber `db` e `ai_manager`
- [ ] Atualizar todos os callers nos routers `api/v1/` e `web/`
- [ ] Verificar: `grep -r "Service()" app/ --include="*.py"` deve retornar zero instâncias globais
- [ ] Adicionar testes com `dependency_overrides` para os 3 serviços principais

### Fase 2 — Fila ARQ (Semanas 1–2, paralelo)

- [ ] Adicionar `arq` e `redis[hiredis]` ao `pyproject.toml`
- [ ] Criar `app/jobs/tasks.py` com `WorkerSettings`
- [ ] Criar `app/services/task_dispatcher.py`
- [ ] Atualizar `app/main.py` lifespan para inicializar ARQ pool
- [ ] Substituir todos os `asyncio.create_task(...)` pelo dispatcher
- [ ] Adicionar serviço `arq-worker` ao `docker-compose.yml`
- [ ] Adicionar serviço `redis` ao `docker-compose.yml`
- [ ] Testar: derrubar processo durante processamento, confirmar retry automático

### Fase 3 — PostgreSQL (Semanas 3–4)

- [ ] Adicionar `asyncpg` ao `pyproject.toml`, remover `aiosqlite`
- [ ] Atualizar `app/database.py` (pool_size, pool_pre_ping, etc.)
- [ ] Criar migração Alembic `008_postgres_fts.py` com o SQL acima
- [ ] Atualizar `app/services/search_service.py` para TSVector
- [ ] Atualizar `app/models/article.py` com índices GIN
- [ ] Atualizar `scripts/vps/` para provisionar PostgreSQL
- [ ] Executar `alembic upgrade head` no ambiente de staging

### Fase 4 — Observabilidade (Semanas 5–6)

- [ ] Criar `app/core/telemetry.py` com setup OpenTelemetry
- [ ] Instrumentar `AIManager` com histograma de latência e fallback counter
- [ ] Instrumentar `FeedAggregatorService` com contador de artigos ingeridos/falhos
- [ ] Adicionar containers Prometheus + Grafana ao `docker-compose.yml`
- [ ] Configurar dashboard Grafana com painéis: latência IA por provedor, fallback rate, jobs ARQ

---

## Referências Cruzadas (Obsidian)

| Padrão utilizado | Fonte no vault |
|------------------|----------------|
| ABC + `@abstractmethod` | `Python Wiki/oop/heranca-e-polimorfismo.md` |
| `Protocol` / duck typing | `Python Wiki/oop/heranca-e-polimorfismo.md` |
| Fallback chain de IA | `Software Archtecture KB/Bhub_Backend_Architecture_Review.md` §3 |
| ARQ como substituto de `asyncio.create_task` | `Software Archtecture KB/Bhub_Backend_Architecture_Review.md` §4 |
| PostgreSQL + TSVector | `Software Archtecture KB/Bhub_Backend_Architecture_Review.md` §4 |

---

*BHub Backend Refactoring Plan v1.0 — pontobhv / Elisson Coimbra*
