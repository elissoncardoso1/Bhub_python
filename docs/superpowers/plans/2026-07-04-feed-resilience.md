# Feed Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar os erros recorrentes de sync de feeds (403 anti-bot, 404/410 URL morta, transitórios matando feeds) endurecendo a camada de fetch, conforme `docs/superpowers/specs/2026-07-04-feed-resilience-design.md`.

**Architecture:** Novo módulo `FeedFetcher` encapsula fetch resiliente (conditional GET, retry tenacity, fallback `curl_cffi` em 403). O `FeedAggregatorService` passa a classificar falhas por tipo (`GONE` dispara redescoberta via trafilatura; `TRANSIENT_ERROR` não incrementa `error_count`). `Feed.needs_sync` ganha sonda de recuperação semanal. `WebScrapingService` ganha fallback trafilatura.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, httpx, feedparser, tenacity, trafilatura, curl_cffi, pytest-asyncio, Alembic.

**Diretório de trabalho:** todos os comandos rodam em `bhub-backend-python/`.

---

### Task 1: Dependências novas

**Files:**
- Modify: `bhub-backend-python/requirements.txt`

- [ ] **Step 1: Adicionar dependências ao requirements.txt**

Após a linha `feedparser>=6.0.11`, adicionar:

```
trafilatura>=2.0.0
curl-cffi>=0.10.0
```

- [ ] **Step 2: Instalar**

Run: `pip install "trafilatura>=2.0.0" "curl-cffi>=0.10.0"`
Expected: instalação sem erro; `python -c "import trafilatura, curl_cffi; print('ok')"` imprime `ok`.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "build: adiciona trafilatura e curl-cffi para resiliência de feeds"
```

---

### Task 2: Colunas de cache HTTP no Feed + migração Alembic

**Files:**
- Modify: `bhub-backend-python/app/models/feed.py` (bloco de colunas, após `max_errors`)
- Create: `bhub-backend-python/alembic/versions/009_feed_http_cache.py`

- [ ] **Step 1: Adicionar colunas ao modelo**

Em `app/models/feed.py`, após o bloco "Contadores de erro" (linha ~79), adicionar:

```python
    # Cache HTTP (conditional GET)
    http_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    http_last_modified: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

- [ ] **Step 2: Criar migração**

Criar `alembic/versions/009_feed_http_cache.py`:

```python
"""Add HTTP conditional-GET cache columns to feeds

Revision ID: 009_feed_http_cache
Revises: 008_postgres_fts
Create Date: 2026-07-04 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_feed_http_cache"
down_revision: Union[str, None] = "008_postgres_fts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona colunas de cache HTTP (ETag / Last-Modified) à tabela feeds."""
    op.add_column("feeds", sa.Column("http_etag", sa.String(255), nullable=True))
    op.add_column("feeds", sa.Column("http_last_modified", sa.String(64), nullable=True))


def downgrade() -> None:
    """Remove colunas de cache HTTP da tabela feeds."""
    op.drop_column("feeds", "http_last_modified")
    op.drop_column("feeds", "http_etag")
```

- [ ] **Step 3: Aplicar migração e verificar**

Run: `alembic upgrade head && sqlite3 bhub.db "PRAGMA table_info(feeds);" | grep http`
Expected: linhas com `http_etag` e `http_last_modified`. (Se `alembic_version` estiver dessincronizado, ver Gotchas no CLAUDE.md: `alembic stamp <rev>` antes.)

- [ ] **Step 4: Commit**

```bash
git add app/models/feed.py alembic/versions/009_feed_http_cache.py
git commit -m "feat(feeds): colunas http_etag/http_last_modified + migração 009"
```

---

### Task 3: Sonda de recuperação em `Feed.needs_sync`

**Files:**
- Modify: `bhub-backend-python/app/models/feed.py:102-124` (propriedade `needs_sync`)
- Create: `bhub-backend-python/tests/test_feed_model_recovery.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `tests/test_feed_model_recovery.py`:

```python
"""Testes da sonda de recuperação de feeds com erro."""

from datetime import datetime, timedelta

from app.models.feed import Feed, SyncFrequency


def make_feed(error_count: int = 0, last_sync_at: datetime | None = None) -> Feed:
    feed = Feed(name="teste", feed_url="https://example.com/feed")
    feed.is_active = True
    feed.error_count = error_count
    feed.max_errors = 5
    feed.sync_frequency = SyncFrequency.HOURLY
    feed.last_sync_at = last_sync_at
    return feed


def test_feed_saudavel_precisa_sync_apos_intervalo():
    feed = make_feed(last_sync_at=datetime.utcnow() - timedelta(hours=2))
    assert feed.needs_sync is True


def test_feed_com_erros_recentes_nao_sincroniza():
    feed = make_feed(error_count=5, last_sync_at=datetime.utcnow() - timedelta(hours=2))
    assert feed.needs_sync is False


def test_feed_com_erros_antigos_entra_em_sonda_de_recuperacao():
    feed = make_feed(error_count=5, last_sync_at=datetime.utcnow() - timedelta(days=8))
    assert feed.needs_sync is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_feed_model_recovery.py -v`
Expected: `test_feed_com_erros_antigos_entra_em_sonda_de_recuperacao` FAIL (retorna False); os outros dois PASS.

- [ ] **Step 3: Implementar sonda de recuperação**

Em `app/models/feed.py`, adicionar constante no topo do módulo (após os imports):

```python
# Feeds desativados por erro voltam a ser sondados após este intervalo
RECOVERY_PROBE_INTERVAL_DAYS = 7
```

Substituir o bloco dentro de `needs_sync`:

```python
        if self.error_count >= self.max_errors:
            return False
```

por:

```python
        from datetime import timedelta

        if self.error_count >= self.max_errors:
            # Sonda de recuperação: em vez de morte permanente, tenta de novo
            # após RECOVERY_PROBE_INTERVAL_DAYS (um sync OK zera error_count).
            if self.last_sync_at is None:
                return True
            probe_interval = timedelta(days=RECOVERY_PROBE_INTERVAL_DAYS)
            return datetime.utcnow() - self.last_sync_at.replace(tzinfo=None) > probe_interval
```

(O `from datetime import timedelta` mais abaixo na propriedade fica redundante — mover o import para o topo da propriedade, uma única vez.)

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_feed_model_recovery.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/feed.py tests/test_feed_model_recovery.py
git commit -m "feat(feeds): sonda de recuperação semanal substitui morte permanente"
```

---

### Task 4: Módulo `FeedFetcher`

**Files:**
- Create: `bhub-backend-python/app/services/feed_fetcher.py`
- Create: `bhub-backend-python/tests/test_feed_fetcher.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `tests/test_feed_fetcher.py`:

```python
"""Testes do fetch resiliente de feeds."""

import httpx
import pytest

from app.services.feed_fetcher import FeedFetcher, FetchResult, FetchStatus


def make_fetcher(handler) -> FeedFetcher:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return FeedFetcher(client=client)


@pytest.mark.asyncio
async def test_fetch_ok_retorna_texto_e_headers_de_cache():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<rss/>",
            headers={"ETag": '"abc123"', "Last-Modified": "Wed, 01 Jan 2026 00:00:00 GMT"},
        )

    fetcher = make_fetcher(handler)
    result = await fetcher.fetch("https://example.com/feed")
    assert result.status is FetchStatus.OK
    assert result.text == "<rss/>"
    assert result.etag == '"abc123"'
    assert result.last_modified == "Wed, 01 Jan 2026 00:00:00 GMT"


@pytest.mark.asyncio
async def test_fetch_envia_conditional_get_e_trata_304():
    seen_headers: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(dict(request.headers))
        return httpx.Response(304)

    fetcher = make_fetcher(handler)
    result = await fetcher.fetch(
        "https://example.com/feed",
        etag='"abc123"',
        last_modified="Wed, 01 Jan 2026 00:00:00 GMT",
    )
    assert result.status is FetchStatus.NOT_MODIFIED
    assert seen_headers.get("if-none-match") == '"abc123"'
    assert seen_headers.get("if-modified-since") == "Wed, 01 Jan 2026 00:00:00 GMT"


@pytest.mark.asyncio
async def test_fetch_aplica_custom_headers():
    seen_headers: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(dict(request.headers))
        return httpx.Response(200, text="<rss/>")

    fetcher = make_fetcher(handler)
    await fetcher.fetch("https://example.com/feed", custom_headers={"X-Api-Key": "s3cr3t"})
    assert seen_headers.get("x-api-key") == "s3cr3t"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [404, 410])
async def test_fetch_404_410_retorna_gone(status_code):
    fetcher = make_fetcher(lambda request: httpx.Response(status_code))
    result = await fetcher.fetch("https://example.com/feed")
    assert result.status is FetchStatus.GONE
    assert str(status_code) in (result.error or "")


@pytest.mark.asyncio
async def test_fetch_5xx_retorna_transitorio():
    fetcher = make_fetcher(lambda request: httpx.Response(502))
    result = await fetcher.fetch("https://example.com/feed")
    assert result.status is FetchStatus.TRANSIENT_ERROR


@pytest.mark.asyncio
async def test_fetch_erro_de_rede_retorna_transitorio():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    fetcher = make_fetcher(handler)
    result = await fetcher.fetch("https://example.com/feed")
    assert result.status is FetchStatus.TRANSIENT_ERROR


@pytest.mark.asyncio
async def test_fetch_403_dispara_fallback_impersonado(monkeypatch):
    calls: list[str] = []

    async def fake_impersonated(self, url, headers):
        calls.append(url)
        return FetchResult(status=FetchStatus.OK, text="<rss/>")

    monkeypatch.setattr(FeedFetcher, "_fetch_impersonated", fake_impersonated)
    fetcher = make_fetcher(lambda request: httpx.Response(403))
    result = await fetcher.fetch("https://example.com/feed")
    assert calls == ["https://example.com/feed"]
    assert result.status is FetchStatus.OK


@pytest.mark.asyncio
async def test_fetch_403_com_fallback_bloqueado_retorna_blocked(monkeypatch):
    async def fake_impersonated(self, url, headers):
        return FetchResult(status=FetchStatus.BLOCKED, error="HTTP 403 (impersonado)")

    monkeypatch.setattr(FeedFetcher, "_fetch_impersonated", fake_impersonated)
    fetcher = make_fetcher(lambda request: httpx.Response(403))
    result = await fetcher.fetch("https://example.com/feed")
    assert result.status is FetchStatus.BLOCKED
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_feed_fetcher.py -v`
Expected: FAIL na coleta — `ModuleNotFoundError: No module named 'app.services.feed_fetcher'`.

- [ ] **Step 3: Implementar `FeedFetcher`**

Criar `app/services/feed_fetcher.py`:

```python
"""
Fetch resiliente de feeds RSS/Atom.

Estratégia (ver docs/superpowers/specs/2026-07-04-feed-resilience-design.md):
- Conditional GET (If-None-Match / If-Modified-Since) para não baixar feed inalterado
- Retry com backoff exponencial apenas para erros de rede
- Fallback com impersonação TLS (curl_cffi) quando o WAF responde 403/429
- Classificação tipada do resultado para a política de erros do aggregator
"""

from dataclasses import dataclass
from enum import Enum

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import log

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

TIMEOUT_SECONDS = 30.0


class FetchStatus(str, Enum):
    """Classificação do resultado de um fetch de feed."""

    OK = "ok"
    NOT_MODIFIED = "not_modified"
    BLOCKED = "blocked"  # 403/429 mesmo após fallback impersonado
    GONE = "gone"  # 404/410 — URL precisa de redescoberta
    TRANSIENT_ERROR = "transient_error"  # 5xx / timeout / erro de rede


@dataclass
class FetchResult:
    status: FetchStatus
    text: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    error: str | None = None


class FeedFetcher:
    """Cliente HTTP resiliente para download de feeds."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        """Baixa um feed classificando o resultado por tipo de falha."""
        headers: dict[str, str] = {}
        if custom_headers:
            headers.update(custom_headers)
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        try:
            response = await self._get_with_retry(url, headers)
        except httpx.HTTPError as e:
            return FetchResult(
                status=FetchStatus.TRANSIENT_ERROR, error=f"Erro de rede: {e}"
            )

        if response.status_code in (403, 429):
            log.info(f"Feed {url} respondeu {response.status_code}; tentando fallback impersonado")
            return await self._fetch_impersonated(url, headers)

        return self._classify_response(
            response.status_code, response.text, dict(response.headers), etag, last_modified
        )

    async def _get_with_retry(self, url: str, headers: dict[str, str]) -> httpx.Response:
        """GET com retry exponencial apenas para falhas de transporte."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(httpx.TransportError),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        ):
            with attempt:
                return await self.client.get(url, headers=headers)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _fetch_impersonated(self, url: str, headers: dict[str, str]) -> FetchResult:
        """Fallback anti-bot: refaz a requisição com fingerprint TLS de navegador."""
        try:
            from curl_cffi.requests import AsyncSession
        except ImportError:
            return FetchResult(
                status=FetchStatus.BLOCKED,
                error="HTTP 403 e curl_cffi não instalado para fallback",
            )

        try:
            async with AsyncSession(impersonate="chrome") as session:
                response = await session.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        except Exception as e:
            return FetchResult(
                status=FetchStatus.BLOCKED, error=f"Fallback impersonado falhou: {e}"
            )

        if response.status_code in (403, 429):
            return FetchResult(
                status=FetchStatus.BLOCKED,
                error=f"HTTP {response.status_code} (impersonado)",
            )
        return self._classify_response(
            response.status_code, response.text, dict(response.headers), None, None
        )

    def _classify_response(
        self,
        status_code: int,
        text: str,
        headers: dict[str, str],
        sent_etag: str | None,
        sent_last_modified: str | None,
    ) -> FetchResult:
        if status_code == 304:
            return FetchResult(
                status=FetchStatus.NOT_MODIFIED,
                etag=sent_etag,
                last_modified=sent_last_modified,
            )
        if status_code in (404, 410):
            return FetchResult(status=FetchStatus.GONE, error=f"HTTP {status_code}")
        if status_code >= 500:
            return FetchResult(status=FetchStatus.TRANSIENT_ERROR, error=f"HTTP {status_code}")
        if status_code >= 400:
            return FetchResult(status=FetchStatus.BLOCKED, error=f"HTTP {status_code}")

        lower_headers = {k.lower(): v for k, v in headers.items()}
        return FetchResult(
            status=FetchStatus.OK,
            text=text,
            etag=lower_headers.get("etag"),
            last_modified=lower_headers.get("last-modified"),
        )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_feed_fetcher.py -v`
Expected: 9 PASS (parametrize gera 2 casos para GONE).

- [ ] **Step 5: Commit**

```bash
git add app/services/feed_fetcher.py tests/test_feed_fetcher.py
git commit -m "feat(feeds): FeedFetcher com conditional GET, retry e fallback anti-bot"
```

---

### Task 5: Política de erros tipada no `FeedAggregatorService`

**Files:**
- Modify: `bhub-backend-python/app/services/feed_aggregator.py` (imports, `__init__`, `close`, `sync_feed`, `test_feed`)
- Create: `bhub-backend-python/tests/test_feed_aggregator_policy.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `tests/test_feed_aggregator_policy.py`:

```python
"""Testes da política de erros tipada do sync de feeds."""

from datetime import datetime

import pytest

from app.models.feed import Feed, SyncFrequency
from app.services.feed_aggregator import FeedAggregatorService
from app.services.feed_fetcher import FetchResult, FetchStatus


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, feed):
        self.feed = feed
        self.committed = False

    async def execute(self, *_args, **_kwargs):
        return FakeResult(self.feed)

    async def commit(self):
        self.committed = True

    async def flush(self):
        pass


def make_feed(error_count: int = 0) -> Feed:
    feed = Feed(name="teste", feed_url="https://example.com/feed")
    feed.id = 1
    feed.is_active = True
    feed.error_count = error_count
    feed.max_errors = 5
    feed.sync_frequency = SyncFrequency.HOURLY
    feed.total_articles = 0
    feed.custom_headers = None
    feed.http_etag = None
    feed.http_last_modified = None
    return feed


class StubFetcher:
    def __init__(self, result: FetchResult):
        self.result = result
        self.calls: list[dict] = []

    async def fetch(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.result

    async def close(self):
        pass


def make_service(feed: Feed, fetch_result: FetchResult) -> FeedAggregatorService:
    service = FeedAggregatorService(db=FakeDB(feed))
    service.fetcher = StubFetcher(fetch_result)
    return service


@pytest.mark.asyncio
async def test_erro_transitorio_nao_incrementa_error_count():
    feed = make_feed(error_count=2)
    service = make_service(
        feed, FetchResult(status=FetchStatus.TRANSIENT_ERROR, error="HTTP 502")
    )
    result = await service.sync_feed(feed_id=1)
    assert result.success is False
    assert feed.error_count == 2
    assert feed.last_error == "HTTP 502"


@pytest.mark.asyncio
async def test_bloqueio_incrementa_error_count():
    feed = make_feed(error_count=0)
    service = make_service(
        feed, FetchResult(status=FetchStatus.BLOCKED, error="HTTP 403 (impersonado)")
    )
    result = await service.sync_feed(feed_id=1)
    assert result.success is False
    assert feed.error_count == 1


@pytest.mark.asyncio
async def test_not_modified_conta_como_sucesso_e_zera_erros():
    feed = make_feed(error_count=3)
    service = make_service(feed, FetchResult(status=FetchStatus.NOT_MODIFIED))
    result = await service.sync_feed(feed_id=1)
    assert result.success is True
    assert result.new_articles == 0
    assert feed.error_count == 0
    assert feed.last_error is None


@pytest.mark.asyncio
async def test_gone_tenta_redescoberta_antes_de_falhar(monkeypatch):
    feed = make_feed(error_count=0)
    service = make_service(feed, FetchResult(status=FetchStatus.GONE, error="HTTP 410"))

    rediscover_calls: list[int] = []

    async def fake_rediscover(f):
        rediscover_calls.append(f.id)
        return None

    monkeypatch.setattr(service, "_try_rediscover", fake_rediscover)
    result = await service.sync_feed(feed_id=1)
    assert rediscover_calls == [1]
    assert result.success is False
    assert feed.error_count == 1


@pytest.mark.asyncio
async def test_sync_ok_persiste_etag_e_last_modified():
    feed = make_feed()
    rss = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>"""
    service = make_service(
        feed,
        FetchResult(
            status=FetchStatus.OK,
            text=rss,
            etag='"novo-etag"',
            last_modified="Thu, 02 Jan 2026 00:00:00 GMT",
        ),
    )
    result = await service.sync_feed(feed_id=1)
    assert result.success is True
    assert feed.http_etag == '"novo-etag"'
    assert feed.http_last_modified == "Thu, 02 Jan 2026 00:00:00 GMT"


@pytest.mark.asyncio
async def test_fetch_recebe_etag_e_custom_headers_do_feed():
    feed = make_feed()
    feed.http_etag = '"etag-salvo"'
    feed.custom_headers = '{"X-Api-Key": "s3cr3t"}'
    service = make_service(feed, FetchResult(status=FetchStatus.NOT_MODIFIED))
    await service.sync_feed(feed_id=1)
    call = service.fetcher.calls[0]
    assert call["etag"] == '"etag-salvo"'
    assert call["custom_headers"] == {"X-Api-Key": "s3cr3t"}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_feed_aggregator_policy.py -v`
Expected: FAIL — `sync_feed` atual não usa `service.fetcher` (erros de atributo/comportamento).

- [ ] **Step 3: Refatorar `feed_aggregator.py`**

3a. Imports — adicionar após `import feedparser`:

```python
import asyncio
import json
```

e após o bloco de imports de `app.`:

```python
from app.services.feed_fetcher import FeedFetcher, FetchResult, FetchStatus
```

3b. `__init__` — após a criação de `self.http_client`, adicionar:

```python
        self.fetcher = FeedFetcher()
```

3c. `close` — substituir o corpo por:

```python
        await self.http_client.aclose()
        await self.fetcher.close()
```

3d. Em `sync_feed`, substituir o bloco (linhas ~113-127 atuais):

```python
        log.info(f"Sincronizando feed: {feed.name}")
        errors: list[str] = []
        new_articles = 0

        try:
            # Fazer requisição HTTP
            response = await self.http_client.get(feed.feed_url)
            response.raise_for_status()

            # Parse do feed
            parsed = feedparser.parse(response.text)
```

por:

```python
        log.info(f"Sincronizando feed: {feed.name}")
        errors: list[str] = []
        new_articles = 0

        fetch_result = await self._fetch_feed(feed)

        # URL morta: tentar redescobrir o feed a partir do site antes de desistir
        if fetch_result.status is FetchStatus.GONE:
            new_url = await self._try_rediscover(feed)
            if new_url:
                feed.feed_url = new_url
                feed.http_etag = None
                feed.http_last_modified = None
                fetch_result = await self._fetch_feed(feed)

        if fetch_result.status is FetchStatus.NOT_MODIFIED:
            feed.last_sync_at = datetime.utcnow()
            feed.last_successful_sync_at = datetime.utcnow()
            feed.error_count = 0
            feed.last_error = None
            feed.articles_last_sync = 0
            await self.db.commit()
            log.info(f"Feed {feed.name} não modificado (HTTP 304)")
            return FeedSyncResult(
                feed_id=feed.id,
                feed_name=feed.name,
                success=True,
                new_articles=0,
                duration_seconds=time.time() - start_time,
            )

        if fetch_result.status is not FetchStatus.OK:
            return await self._record_fetch_failure(feed, fetch_result, start_time)

        try:
            # Parse do feed
            parsed = feedparser.parse(fetch_result.text)
```

3e. Ainda em `sync_feed`, no bloco de sucesso (onde hoje está `feed.last_sync_at = datetime.utcnow()` após o loop de entries), adicionar imediatamente antes de `feed.last_sync_at = ...`:

```python
            # Persistir validadores de cache HTTP para conditional GET
            feed.http_etag = fetch_result.etag
            feed.http_last_modified = fetch_result.last_modified
```

3f. Adicionar os métodos auxiliares ao final da classe (antes de `test_feed`):

```python
    def _parse_custom_headers(self, feed: Feed) -> dict[str, str] | None:
        """Desserializa custom_headers (JSON) do feed, se houver."""
        if not feed.custom_headers:
            return None
        try:
            headers = json.loads(feed.custom_headers)
            if isinstance(headers, dict):
                return {str(k): str(v) for k, v in headers.items()}
        except (ValueError, TypeError) as e:
            log.warning(f"custom_headers inválido no feed {feed.name}: {e}")
        return None

    async def _fetch_feed(self, feed: Feed) -> FetchResult:
        """Fetch resiliente usando os validadores de cache persistidos no feed."""
        return await self.fetcher.fetch(
            feed.feed_url,
            etag=feed.http_etag,
            last_modified=feed.http_last_modified,
            custom_headers=self._parse_custom_headers(feed),
        )

    async def _record_fetch_failure(
        self, feed: Feed, fetch_result: FetchResult, start_time: float
    ) -> FeedSyncResult:
        """Registra falha de fetch. Erros transitórios não incrementam error_count."""
        from app.core.telemetry import record_feed_failed

        record_feed_failed(feed.name)

        error_msg = fetch_result.error or fetch_result.status.value
        feed.last_sync_at = datetime.utcnow()
        feed.last_error = error_msg
        if fetch_result.status is not FetchStatus.TRANSIENT_ERROR:
            feed.error_count += 1

        await self.db.commit()
        log.warning(f"Falha ao sincronizar feed {feed.name}: {error_msg}")

        return FeedSyncResult(
            feed_id=feed.id,
            feed_name=feed.name,
            success=False,
            errors=[error_msg],
            duration_seconds=time.time() - start_time,
        )

    async def _try_rediscover(self, feed: Feed) -> str | None:
        """Placeholder implementado na Task 6 — por ora não redescobre."""
        return None
```

3g. Em `test_feed`, substituir:

```python
            response = await self.http_client.get(feed_url)
            response.raise_for_status()

            parsed = feedparser.parse(response.text)
```

por:

```python
            fetch_result = await self.fetcher.fetch(feed_url)
            if fetch_result.status is not FetchStatus.OK:
                return FeedTestResult(
                    success=False,
                    error=fetch_result.error or fetch_result.status.value,
                )

            parsed = feedparser.parse(fetch_result.text)
```

- [ ] **Step 4: Rodar e ver passar (inclui regressão)**

Run: `pytest tests/test_feed_aggregator_policy.py tests/test_feed_aggregator_minimal.py -v`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/feed_aggregator.py tests/test_feed_aggregator_policy.py
git commit -m "feat(feeds): política de erros tipada + conditional GET no aggregator"
```

---

### Task 6: Redescoberta de feed via trafilatura

**Files:**
- Modify: `bhub-backend-python/app/services/feed_aggregator.py` (substituir placeholder `_try_rediscover`, novo `_rediscover_feed_url`)
- Create: `bhub-backend-python/tests/test_feed_rediscovery.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `tests/test_feed_rediscovery.py`:

```python
"""Testes da redescoberta de URL de feed quando a atual retorna 404/410."""

import pytest

from app.models.feed import Feed, SyncFrequency
from app.services.feed_aggregator import FeedAggregatorService
from app.services.feed_fetcher import FetchResult, FetchStatus

VALID_RSS = (
    '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
    "<item><title>artigo</title><link>https://example.com/a</link></item>"
    "</channel></rss>"
)


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    """DB fake: primeiro execute retorna o feed; o check de duplicata retorna dup."""

    def __init__(self, feed, duplicate=None):
        self.feed = feed
        self.duplicate = duplicate
        self.calls = 0

    async def execute(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return FakeResult(self.feed)
        return FakeResult(self.duplicate)

    async def commit(self):
        pass

    async def flush(self):
        pass


class MappingFetcher:
    """Fetcher fake que responde por URL."""

    def __init__(self, responses: dict[str, FetchResult]):
        self.responses = responses

    async def fetch(self, url, **_kwargs):
        return self.responses[url]

    async def close(self):
        pass


def make_feed() -> Feed:
    feed = Feed(name="teste", feed_url="https://example.com/feed-antigo")
    feed.id = 1
    feed.is_active = True
    feed.error_count = 0
    feed.max_errors = 5
    feed.sync_frequency = SyncFrequency.HOURLY
    feed.total_articles = 0
    feed.custom_headers = None
    feed.http_etag = None
    feed.http_last_modified = None
    feed.website_url = "https://example.com"
    return feed


@pytest.mark.asyncio
async def test_rediscover_valida_candidato_e_retorna_url(monkeypatch):
    feed = make_feed()
    service = FeedAggregatorService(db=FakeDB(feed))
    service.fetcher = MappingFetcher(
        {"https://example.com/feed-novo": FetchResult(status=FetchStatus.OK, text=VALID_RSS)}
    )
    monkeypatch.setattr(
        "trafilatura.feeds.find_feed_urls",
        lambda url: ["https://example.com/feed-novo"],
    )
    new_url = await service._rediscover_feed_url(feed)
    assert new_url == "https://example.com/feed-novo"


@pytest.mark.asyncio
async def test_rediscover_ignora_candidato_igual_ou_invalido(monkeypatch):
    feed = make_feed()
    service = FeedAggregatorService(db=FakeDB(feed))
    service.fetcher = MappingFetcher(
        {"https://example.com/feed-quebrado": FetchResult(status=FetchStatus.GONE, error="HTTP 404")}
    )
    monkeypatch.setattr(
        "trafilatura.feeds.find_feed_urls",
        lambda url: ["https://example.com/feed-antigo", "https://example.com/feed-quebrado"],
    )
    assert await service._rediscover_feed_url(feed) is None


@pytest.mark.asyncio
async def test_rediscover_sem_website_url_retorna_none():
    feed = make_feed()
    feed.website_url = None
    service = FeedAggregatorService(db=FakeDB(feed))
    assert await service._rediscover_feed_url(feed) is None


@pytest.mark.asyncio
async def test_try_rediscover_respeita_unique_constraint(monkeypatch):
    feed = make_feed()
    outro_feed = make_feed()
    outro_feed.id = 2
    db = FakeDB(feed, duplicate=outro_feed)
    service = FeedAggregatorService(db=db)
    db.calls = 1  # simula que o select do próprio feed já ocorreu

    async def fake_rediscover(_feed):
        return "https://example.com/feed-novo"

    monkeypatch.setattr(service, "_rediscover_feed_url", fake_rediscover)
    assert await service._try_rediscover(feed) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_feed_rediscovery.py -v`
Expected: FAIL — `_rediscover_feed_url` não existe; `_try_rediscover` retorna sempre None mas o teste de unique espera a lógica de verificação (falha porque monkeypatch de `_rediscover_feed_url` exige o atributo).

- [ ] **Step 3: Implementar redescoberta**

Em `app/services/feed_aggregator.py`, substituir o placeholder `_try_rediscover` por:

```python
    async def _try_rediscover(self, feed: Feed) -> str | None:
        """Redescobre a URL do feed e valida contra a unique constraint de feed_url."""
        new_url = await self._rediscover_feed_url(feed)
        if not new_url:
            return None

        dup = await self.db.execute(
            select(Feed).where(Feed.feed_url == new_url, Feed.id != feed.id)
        )
        if dup.scalar_one_or_none() is not None:
            log.warning(
                f"Feed {feed.name}: URL redescoberta {new_url} já pertence a outro feed"
            )
            return None

        log.info(f"Feed {feed.name}: URL redescoberta {feed.feed_url} -> {new_url}")
        return new_url

    async def _rediscover_feed_url(self, feed: Feed) -> str | None:
        """Procura feeds no website do periódico e valida o primeiro candidato útil."""
        if not feed.website_url:
            return None

        try:
            from trafilatura import feeds as trafilatura_feeds

            # find_feed_urls é síncrono e faz I/O de rede — rodar em thread
            candidates = await asyncio.to_thread(
                trafilatura_feeds.find_feed_urls, feed.website_url
            )
        except Exception as e:
            log.warning(f"Redescoberta de feed falhou para {feed.name}: {e}")
            return None

        for candidate in candidates or []:
            if candidate == feed.feed_url:
                continue
            try:
                result = await self.fetcher.fetch(candidate)
            except Exception as e:
                log.debug(f"Candidato {candidate} falhou: {e}")
                continue
            if result.status is FetchStatus.OK and result.text:
                parsed = feedparser.parse(result.text)
                if parsed.entries:
                    return candidate

        return None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_feed_rediscovery.py tests/test_feed_aggregator_policy.py -v`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/feed_aggregator.py tests/test_feed_rediscovery.py
git commit -m "feat(feeds): redescoberta automática de URL de feed em 404/410"
```

---

### Task 7: Fallback trafilatura no `WebScrapingService`

**Files:**
- Modify: `bhub-backend-python/app/services/web_scraper.py` (fim de `scrape_url`, novo método)
- Create: `bhub-backend-python/tests/test_web_scraper_trafilatura.py`

- [ ] **Step 1: Escrever teste que falha**

Criar `tests/test_web_scraper_trafilatura.py`:

```python
"""Testes do fallback trafilatura na extração de artigos."""

from app.services.web_scraper import WebScrapingService

HTML_SEM_META = """
<html><head><title>Página</title></head><body>
<div id="conteudo">
<h1>Efeitos do reforçamento diferencial em contexto clínico</h1>
<p>Este estudo investigou os efeitos do reforçamento diferencial de comportamentos
alternativos em um contexto clínico com participantes diagnosticados com TEA.
Os resultados indicaram redução consistente de comportamentos-problema.</p>
<p>Foram conduzidas três fases experimentais com delineamento de linha de base
múltipla entre participantes, com medidas repetidas de frequência e duração.
A integridade do procedimento foi avaliada em todas as sessões experimentais.</p>
<p>Discutem-se implicações para a prática clínica baseada em evidências e
limitações metodológicas do delineamento adotado neste estudo.</p>
</div>
</body></html>
"""


def test_fallback_preenche_abstract_quando_seletores_falham():
    service = WebScrapingService()
    data = {
        "title": "Sem título",
        "abstract": None,
        "authors": [],
    }
    service._apply_trafilatura_fallback(HTML_SEM_META, data)
    assert data["abstract"] is not None
    assert "reforçamento diferencial" in data["abstract"]
    assert data["title"] != "Sem título"


def test_fallback_nao_sobrescreve_dados_existentes():
    service = WebScrapingService()
    data = {
        "title": "Título original",
        "abstract": "Abstract original",
        "authors": [{"name": "Autora"}],
    }
    service._apply_trafilatura_fallback(HTML_SEM_META, data)
    assert data["title"] == "Título original"
    assert data["abstract"] == "Abstract original"
    assert data["authors"] == [{"name": "Autora"}]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_web_scraper_trafilatura.py -v`
Expected: FAIL — `AttributeError: 'WebScrapingService' object has no attribute '_apply_trafilatura_fallback'`.

- [ ] **Step 3: Implementar fallback**

Em `app/services/web_scraper.py`, dentro de `scrape_url`, após a montagem do dict `data` e antes do `log.info(f"Scraping concluído...")`, adicionar:

```python
        # Fallback: quando os seletores não encontram título/abstract, tenta trafilatura
        if data["title"] == "Sem título" or not data["abstract"]:
            self._apply_trafilatura_fallback(html, data)
```

Adicionar o método ao final da classe:

```python
    def _apply_trafilatura_fallback(self, html: str, data: dict) -> None:
        """
        Completa campos vazios usando trafilatura (extração em cascata,
        estado da arte em boilerplate removal). Nunca sobrescreve dados existentes.
        """
        try:
            import trafilatura

            extracted = trafilatura.bare_extraction(html, with_metadata=True)
        except Exception as e:
            log.warning(f"Fallback trafilatura falhou: {e}")
            return

        if not extracted:
            return

        if data.get("title") in (None, "", "Sem título") and extracted.title:
            data["title"] = extracted.title

        if not data.get("abstract") and extracted.text:
            text = extracted.text.strip()
            data["abstract"] = text[:5000] if len(text) > 5000 else text

        if not data.get("authors") and extracted.author:
            data["authors"] = [
                a.strip() for a in extracted.author.split(";") if a.strip()
            ]
```

- [ ] **Step 4: Rodar e ver passar (inclui regressão do scraper)**

Run: `pytest tests/test_web_scraper_trafilatura.py tests/test_web_scraper_minimal.py -v`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/web_scraper.py tests/test_web_scraper_trafilatura.py
git commit -m "feat(scraper): trafilatura como fallback de extração de conteúdo"
```

---

### Task 8: Verificação final

**Files:** nenhum novo.

- [ ] **Step 1: Suíte completa**

Run: `pytest tests/ -v`
Expected: todos os testes passam (97 pré-existentes + novos).

- [ ] **Step 2: Lint e tipos nos arquivos alterados**

Run: `ruff check app/services/feed_fetcher.py app/services/feed_aggregator.py app/services/web_scraper.py app/models/feed.py && mypy app/services/feed_fetcher.py`
Expected: sem erros novos (o repositório tem 112 erros ruff pré-existentes em outros arquivos — não corrigir fora do escopo).

- [ ] **Step 3: Commit final (se houver ajustes de lint)**

```bash
git add -A && git commit -m "chore: ajustes de lint da resiliência de feeds"
```
