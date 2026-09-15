"""Testes de injeção de dependências do FeedAggregatorService (Task 7 — T2.4).

Casos adiados da Task 6 (ruling do controller):
- FeedAggregator aceita parser fake;
- FeedAggregator aceita fetcher fake.

Extras do mapa de instanciação (docs/architecture/SERVICE_INSTANTIATION_MAP.md):
- defaults preservam as instâncias concretas (call sites atuais não quebram);
- ``http_client`` injetável com semântica de dono (``close`` não fecha o que
  não criou — paridade com ``FeedFetcher``).
"""

from __future__ import annotations

import httpx

from app.models.feed import Feed, SyncFrequency
from app.services.article_parser import ArticleParserService
from app.services.feed_aggregator import FeedAggregatorService
from app.services.feed_fetcher import FeedFetcher, FetchResult, FetchStatus

RSS_ONE_ITEM = (
    '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
    "<item><title>artigo</title><link>https://example.com/a</link></item>"
    "</channel></rss>"
)


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return [] if self.value is None else [self.value]

    def first(self):
        return self.value


class FakeNested:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


class FakeDB:
    """Sessão fake: 1º execute devolve o feed; demais consultas não acham nada."""

    def __init__(self, feed=None):
        self.feed = feed
        self.added = []
        self.calls = 0

    def add(self, obj):
        self.added.append(obj)

    def begin_nested(self):
        return FakeNested()

    async def execute(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return FakeResult(self.feed)
        return FakeResult(None)

    async def flush(self):
        pass

    async def commit(self):
        pass


class FakeParser:
    """Parser fake: registra chamadas e devolve dados canônicos."""

    def __init__(self):
        self.external_id_calls: list[tuple] = []
        self.parse_calls: list[tuple] = []

    def generate_external_id(self, entry, feed_id):
        self.external_id_calls.append((entry, feed_id))
        return f"feed_{feed_id}_fake"

    def parse_entry(self, entry, journal_name=None):
        self.parse_calls.append((entry, journal_name))
        return {
            "title": "Título do Parser Fake",
            "abstract": None,
            # autores vazios: evita o fallback de scraping (rede) no teste
            "authors": [],
            "url": "https://example.com/artigo",
            "publication_date": None,
            "keywords": None,
            "doi": None,
            "journal": None,
            "language": "en",
            "image_url": None,
            "is_open_access": False,
            "pdf_url": None,
        }

    def parse_html_authors(self, _html):  # pragma: no cover
        raise AssertionError("parser real de HTML não deveria ser usado")


class FakeFetcher:
    """Fetcher fake que responde por URL e registra as chamadas."""

    def __init__(self, responses: dict[str, FetchResult]):
        self.responses = responses
        self.calls: list[dict] = []

    async def fetch(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses[url]

    async def close(self):
        pass


def make_feed() -> Feed:
    feed = Feed(name="teste", feed_url="https://example.com/feed")
    feed.id = 1
    feed.is_active = True
    feed.error_count = 0
    feed.max_errors = 5
    feed.sync_frequency = SyncFrequency.HOURLY
    feed.total_articles = 0
    feed.custom_headers = None
    feed.http_etag = None
    feed.http_last_modified = None
    feed.website_url = None
    return feed


async def test_feed_aggregator_aceita_parser_fake():
    """O parser fake injetado é usado no fluxo real de sync (não só atribuído)."""
    feed = make_feed()
    parser = FakeParser()
    fetcher = FakeFetcher(
        {"https://example.com/feed": FetchResult(status=FetchStatus.OK, text=RSS_ONE_ITEM)}
    )
    service = FeedAggregatorService(db=FakeDB(feed), parser=parser, fetcher=fetcher)

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert service.parser is parser
    # o fake participou do processamento da entrada
    assert len(parser.external_id_calls) == 1
    assert len(parser.parse_calls) == 1
    # o artigo criado carrega os dados devolvidos pelo fake
    assert service.db.added[0].title == "Título do Parser Fake"


async def test_feed_aggregator_aceita_fetcher_fake():
    """O fetcher fake injetado responde pelo fetch — sem rede e sem patch."""
    feed = make_feed()
    fetcher = FakeFetcher(
        {"https://example.com/feed": FetchResult(status=FetchStatus.GONE, error="HTTP 410")}
    )
    service = FeedAggregatorService(db=FakeDB(feed), fetcher=fetcher)

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert service.fetcher is fetcher
    assert fetcher.calls[0]["url"] == "https://example.com/feed"
    # política de erros aplicada a partir do resultado do fake
    assert feed.last_error == "HTTP 410"
    assert feed.error_count == 1


async def test_defaults_mantem_instancias_concretas():
    """Sem injeção, o construtor cria as instâncias concretas de hoje."""
    service = FeedAggregatorService(db=FakeDB())

    assert isinstance(service.parser, ArticleParserService)
    assert isinstance(service.fetcher, FeedFetcher)
    assert isinstance(service.http_client, httpx.AsyncClient)

    client = service.http_client
    await service.close()
    assert client.is_closed  # client próprio é fechado pelo serviço


async def test_http_client_injetavel_pertence_ao_chamador():
    """``close`` não fecha um ``http_client`` injetado (dono é o chamador)."""

    class FakeClient:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    client = FakeClient()
    service = FeedAggregatorService(db=FakeDB(), http_client=client)

    assert service.http_client is client
    await service.close()
    assert client.closed is False
