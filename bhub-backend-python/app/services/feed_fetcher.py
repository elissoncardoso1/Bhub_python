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
            log.info(
                f"Feed {url} respondeu {response.status_code}; tentando fallback impersonado"
            )
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
