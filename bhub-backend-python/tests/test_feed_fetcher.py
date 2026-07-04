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
