"""Testes da política de erros tipada do sync de feeds."""

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
