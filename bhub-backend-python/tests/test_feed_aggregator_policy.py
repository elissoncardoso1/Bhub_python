"""Testes da política de erros tipada do sync de feeds."""

from contextlib import asynccontextmanager
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

    @asynccontextmanager
    async def begin_nested(self):
        yield None


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
    return FeedAggregatorService(db=FakeDB(feed), fetcher=StubFetcher(fetch_result))


@pytest.mark.asyncio
async def test_erro_transitorio_nao_incrementa_error_count():
    feed = make_feed(error_count=2)
    service = make_service(feed, FetchResult(status=FetchStatus.TRANSIENT_ERROR, error="HTTP 502"))
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


# --- Resposta HTTP 200 cujo corpo NÃO é RSS/Atom ---------------------------
# A Springer passou a devolver o challenge anti-bot da Fastly com HTTP 200 e
# corpo HTML. Sem validação de conteúdo o sync marcava sucesso, zerava
# error_count e avançava last_successful_sync_at — escondendo ~7 semanas sem
# ingestão de periódicos.

CHALLENGE_HTML = """<!DOCTYPE html>
<html lang="en">
  <head><title>Client Challenge</title></head>
  <body><p>Please enable JavaScript to proceed.</p></body>
</html>"""

RSS_COM_ITEM = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
  <item><title>Artigo</title><link>https://example.com/a</link></item>
</channel></rss>"""

RSS_VAZIO = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>"""

ATOM_VAZIO = (
    """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title></feed>"""
)

SYNC_ANTERIOR = datetime(2026, 8, 4, 12, 0, 0)


def make_feed_com_sucesso_anterior(error_count: int = 0) -> Feed:
    feed = make_feed(error_count=error_count)
    feed.last_successful_sync_at = SYNC_ANTERIOR
    return feed


@pytest.mark.asyncio
async def test_html_com_http_200_nao_conta_como_sucesso():
    feed = make_feed_com_sucesso_anterior(error_count=0)
    service = make_service(
        feed,
        FetchResult(
            status=FetchStatus.OK,
            text=CHALLENGE_HTML,
            etag='"challenge"',
        ),
    )

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert result.new_articles == 0
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"


@pytest.mark.asyncio
async def test_html_com_http_200_incrementa_error_count():
    feed = make_feed_com_sucesso_anterior(error_count=2)
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=CHALLENGE_HTML))

    await service.sync_feed(feed_id=1)

    assert feed.error_count == 3


@pytest.mark.asyncio
async def test_html_com_http_200_preserva_last_successful_sync_at():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=CHALLENGE_HTML))

    await service.sync_feed(feed_id=1)

    assert feed.last_successful_sync_at == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_html_sem_doctype_nem_content_type_tambem_falha():
    """A detecção não pode depender do header: corpo HTML cru também é inválido."""
    feed = make_feed_com_sucesso_anterior()
    service = make_service(
        feed,
        FetchResult(status=FetchStatus.OK, text="<html><body>bloqueado</body></html>"),
    )

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"
    assert feed.last_successful_sync_at == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_corpo_vazio_nao_conta_como_sucesso():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=""))

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"
    assert feed.last_successful_sync_at == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_corpo_json_nao_conta_como_sucesso():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text='{"items": []}'))

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"


@pytest.mark.asyncio
async def test_rss_valido_vazio_continua_sendo_sucesso():
    """Feed estruturalmente válido com 0 itens NÃO é falha (§9 do hotfix)."""
    feed = make_feed_com_sucesso_anterior(error_count=3)
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=RSS_VAZIO))

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert result.new_articles == 0
    assert feed.error_count == 0
    assert feed.last_successful_sync_at != SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_atom_valido_vazio_continua_sendo_sucesso():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=ATOM_VAZIO))

    result = await service.sync_feed(feed_id=1)

    assert result.success is True


@pytest.mark.asyncio
async def test_rss_valido_com_item_continua_sendo_processado(monkeypatch):
    """Feed saudável não pode regredir: as entradas seguem sendo processadas."""
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=RSS_COM_ITEM))

    async def fake_process(_feed, _entry):
        return 42, {"is_open_access": False}

    monkeypatch.setattr(service, "_process_feed_entry", fake_process)

    dispatched: list[int] = []

    async def fake_dispatch(article_id):
        dispatched.append(article_id)
        return "job-1"

    monkeypatch.setattr("app.services.feed_aggregator.dispatch_classify_article", fake_dispatch)

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert result.new_articles == 1
    assert dispatched == [42]
