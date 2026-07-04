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
        lambda _url: ["https://example.com/feed-novo"],
    )
    new_url = await service._rediscover_feed_url(feed)
    assert new_url == "https://example.com/feed-novo"


@pytest.mark.asyncio
async def test_rediscover_ignora_candidato_igual_ou_invalido(monkeypatch):
    feed = make_feed()
    service = FeedAggregatorService(db=FakeDB(feed))
    service.fetcher = MappingFetcher(
        {
            "https://example.com/feed-quebrado": FetchResult(
                status=FetchStatus.GONE, error="HTTP 404"
            )
        }
    )
    monkeypatch.setattr(
        "trafilatura.feeds.find_feed_urls",
        lambda _url: ["https://example.com/feed-antigo", "https://example.com/feed-quebrado"],
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
