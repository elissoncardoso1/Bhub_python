"""Ingestão de periódicos científicos via API REST do Crossref.

Contexto e decisão em ``docs/adr/0007-crossref-para-periodicos.md``.

O objetivo deste módulo é **um só**: buscar works de um ISSN e entregá-los no
mesmo formato de dicionário que o ``feedparser`` produz, para que o
``ArticleParserService`` já existente faça o parse sem nenhuma duplicação de
regra de limpeza, autores, idioma ou título.

Daí vêm três decisões que valem registro no código:

1. **Nada de dataclass intermediária.** O contrato é "dict no formato
   feedparser" — a mesma moeda que ``sync_feed`` já consome no laço de
   ``parsed.entries``. Uma dataclass própria obrigaria a escrever um segundo
   parser de artigo.
2. **``FetchResult``/``FetchStatus`` reaproveitados.** As falhas do Crossref
   caem no ``_record_fetch_failure`` já validado pelo ADR-0006, sem ramo novo
   de política de erro.
3. **Sem ``pdf_url``.** O ``link`` do Crossref aponta para o PDF hospedado na
   editora — o mesmo host que responde 403. Mapeá-lo enfileiraria downloads
   fadados a falhar e ampliaria a superfície de bloqueio de IP.
"""

from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.config import settings
from app.core.logging import log
from app.services.feed_fetcher import FetchResult, FetchStatus

# Endpoint de works de um periódico, indexado por ISSN.
CROSSREF_JOURNAL_WORKS = "https://api.crossref.org/journals/{issn}/works"
# Endpoint de metadados do periódico em si (validação de ISSN).
CROSSREF_JOURNAL = "https://api.crossref.org/journals/{issn}"

# Campos pedidos ao Crossref. Reduz o payload e deixa explícito o que é usado:
# qualquer campo fora desta lista não é lido pelo adaptador.
#
# `language` NÃO está aqui porque não é um `select` válido nesta rota — o
# Crossref responde 400 `select-not-available` e derruba a página inteira. O
# idioma do artigo fica com a heurística do `ArticleParserService`, que já
# detecta português pelos caracteres do título e usa "en" como default.
CROSSREF_SELECT = "DOI,title,author,published,container-title,abstract,URL,type,license"

# Janela usada quando o feed nunca sincronizou com sucesso.
CROSSREF_INITIAL_LOOKBACK_DAYS = 90
# Janela usada depois de um sync bem-sucedido; cobre correções retroativas de
# metadados sem reprocessar o histórico.
CROSSREF_INCREMENTAL_LOOKBACK_DAYS = 7

# Um work cujo ``type`` não seja este é ignorado: o feed de periódico entrega
# artigos, não editoriais/erratas/retratações com DOI próprio.
CROSSREF_KEEP_TYPES = {"journal-article"}

# Correções e retratações chegam ao Crossref como ``journal-article`` e só se
# distinguem pelo título. Publicá-las como artigo colocaria "Correction to: ..."
# na listagem como se fosse conteúdo novo.
#
# O padrão exige o **delimitador** que acompanha o marcador, porque ele é o que
# separa o aviso do título original. Formas medidas no Crossref (2026-09-25):
# ``Correction: X``, ``Correction to: X``, ``Correction to ‘X’``,
# ``Correction to “X”``. Sem o delimitador, títulos legítimos seriam descartados
# — "Correction to behavior is possible", "The Performance Diagnostic
# Checklist: a Correction", "EFFECTS OF IMMEDIATE SELF‐CORRECTION, ...".
_CORRECTION_TITLE_PATTERN = re.compile(
    r"^\s*(?:correction|erratum|retraction|corrigendum|addendum)s?"
    r"\b\s*(?:to\s*)?(?:[:：]|[‘’“”\"'])\s*\S",
    re.I,
)

# Licença que caracteriza acesso aberto. Só é considerada quando explícita:
# prefere-se subestimar a marcar conteúdo pago como aberto.
_OPEN_LICENSE_PATTERN = re.compile(r"creativecommons\.org|/licenses?/by|/publicdomain/", re.I)

# Autores no Crossref vêm como {"given": "Paige", "family": "O'Neill"}.
_JATS_TAG_PATTERN = re.compile(r"</?jats:[^>]*>")
_AFFILIATION_TAG_PATTERN = re.compile(r"<jats:aff[^>]*>.*?</jats:aff>", re.I | re.S)


def _clean_markup(value: str | None) -> str | None:
    """Remove tags JATS/HTML de um campo textual do Crossref.

    Abstracts do Crossref vêm em JATS XML (``<jats:title>``, ``<jats:p>``,
    ``<jats:italic>``). O ``ArticleParserService`` limpa HTML genérico, mas não
    conhece o prefixo ``jats:``.
    """
    if not value:
        return None
    text = _AFFILIATION_TAG_PATTERN.sub(" ", value)
    text = _JATS_TAG_PATTERN.sub(" ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    # ``&lt;jats:p&gt;`` escapado precisa de uma segunda passada.
    text = html.unescape(text)
    text = re.sub(r"</?jats:[^>]*>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _normalize_doi(doi: str | None) -> str | None:
    """Normaliza DOI para a forma canônica em minúsculas e sem prefixo de URL.

    O DOI é a semente do ``external_id``: sem normalizar, ``10.1002/JABA.1`` e
    ``10.1002/jaba.1`` gerariam dois artigos distintos para o mesmo trabalho.
    """
    if not doi:
        return None
    normalized = doi.strip()
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", normalized, flags=re.I)
    normalized = re.sub(r"^doi:\s*", "", normalized, flags=re.I)
    return normalized.lower() or None


def _publication_date(message: dict[str, Any]) -> str | None:
    """Extrai a data de publicação no formato que o ``parse_entry`` entende.

    ``published.date-parts`` é uma lista de listas e pode vir truncada: ``[2015]``
    (só ano), ``[2026, 8]`` (ano e mês) ou ``[2026, 8, 17]``. Completar o que
    falta com 1 é a convenção do próprio Crossref para datas imprecisas.
    """
    parts = (message.get("published") or {}).get("date-parts") or [[]]
    values = list(parts[0]) if parts and parts[0] else []
    if not values or not values[0]:
        return None

    year = int(values[0])
    month = int(values[1]) if len(values) > 1 and values[1] else 1
    day = int(values[2]) if len(values) > 2 and values[2] else 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        # Mês/dia fora de faixa (dado ruim da editora): degradar para o ano.
        return date(year, 1, 1).isoformat()


def _authors(message: dict[str, Any]) -> list[dict[str, str]]:
    """Monta a lista de autores no formato ``[{"name": ...}]`` do feedparser.

    Autores sem ``family`` nem ``given`` (só ``name``, comum em editoras que
    depositam instituições) são aproveitados quando há nome utilizável.
    """
    authors: list[dict[str, str]] = []
    for author in message.get("author") or []:
        if not isinstance(author, dict):
            continue
        if author.get("family"):
            name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
        else:
            name = author.get("name") or ""
        name = re.sub(r"\s+", " ", name).strip()
        if name:
            authors.append({"name": name})
    return authors


def work_to_entry(message: dict[str, Any]) -> dict[str, Any] | None:
    """Converte um work do Crossref em uma entrada no formato do feedparser.

    Retorna ``None`` para itens inutilizáveis (sem DOI ou sem título), que
    devem ser descartados em vez de gerar artigo com identificador instável.
    """
    doi = _normalize_doi(message.get("DOI"))
    titles = message.get("title") or []
    title = (titles[0] if isinstance(titles, list) and titles else titles) or ""
    title = str(title).strip() if title else ""
    if not doi or not title:
        return None
    if _CORRECTION_TITLE_PATTERN.match(title):
        return None

    container = message.get("container-title") or []
    journal = (container[0] if isinstance(container, list) and container else container) or ""

    # ``dc_rights`` é onde o ``ArticleParserService._detect_open_access`` procura
    # menções a acesso aberto. A URL do CrossRef usa ``creativecommons.org``
    # (sem espaço), que o padrão "creative commons" do parser não casa — por isso
    # a string é materializada aqui, na única grafia que o detector entende.
    rights = [
        (item or {}).get("URL") if isinstance(item, dict) else item
        for item in (message.get("license") or [])
    ]
    has_open_license = any(
        isinstance(item, str) and _OPEN_LICENSE_PATTERN.search(item) for item in rights
    )

    entry: dict[str, Any] = {
        # ``id`` é a semente do external_id e o que garante a deduplicação
        # entre republicações (Early View -> número fechado) do mesmo DOI.
        "id": f"doi:{doi}",
        # ``link`` -> Article.original_url. Aponta para doi.org, que resolve
        # para a editora sem exigir requisição nossa.
        "link": message.get("URL") or f"https://doi.org/{doi}",
        "title": title,
        "summary": _clean_markup(message.get("abstract")),
        "published": _publication_date(message),
        "authors": _authors(message),
        "doi": doi,
        "journal": str(journal).strip() if journal else None,
        "language": (message.get("language") or "").split("-")[0].split("_")[0] or None,
        "dc_rights": "Creative Commons" if has_open_license else None,
        # ``pdf_url`` deliberadamente ausente: ver cabeçalho do módulo.
    }
    return entry


class CrossrefSource:
    """Cliente mínimo da API REST do Crossref, focado em um ISSN."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=settings.crossref_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": settings.crossref_user_agent,
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    def _params(self, *, select: str | None = None, **extra: Any) -> dict[str, Any]:
        """Parâmetros comuns: identificação no pool 'polite' do Crossref.

        ``select`` é opcional porque **só a rota de works o aceita**: a rota
        ``/journals/{issn}`` responde 400 ``parameter-not-allowed`` se receber
        ``select``.
        """
        params: dict[str, Any] = {}
        if select:
            params["select"] = select
        if settings.crossref_mailto:
            params["mailto"] = settings.crossref_mailto
        params.update(extra)
        return params

    async def fetch_works(
        self,
        issn: str | None,
        *,
        last_successful_sync_at: datetime | None,
        now: datetime | None = None,
    ) -> FetchResult:
        """Busca os works recentes de um ISSN, paginando até ``crossref_max_pages``.

        ``issn`` é anulável de propósito: um feed marcado como ``CROSSREF`` sem
        ISSN configurado é um erro de cadastro, e devolver falha permanente aqui
        é melhor que deixar o ``TypeError`` estourar no meio do sync.

        A janela é ``[from-pub-date, until-pub-date]``. O ``until`` limita a
        coleta a hoje: o Crossref aceita (e editoras depositam) datas futuras em
        publicação antecipada, e elas poluiriam a listagem por data.
        """
        if not issn:
            return FetchResult(
                status=FetchStatus.INVALID_CONTENT,
                error="Feed sem ISSN configurado para ingestão via Crossref",
            )

        reference = now or datetime.utcnow()
        if last_successful_sync_at is None:
            lookback_days = CROSSREF_INITIAL_LOOKBACK_DAYS
        else:
            # Overlap deliberado: cobre correções retroativas de metadados. O
            # external_id derivado do DOI descarta o que já foi ingerido.
            lookback_days = CROSSREF_INCREMENTAL_LOOKBACK_DAYS

        reference_date = reference.date()
        since = reference_date - timedelta(days=lookback_days)
        filter_value = (
            f"from-pub-date:{since.isoformat()},"
            f"until-pub-date:{reference_date.isoformat()},"
            f"type:journal-article"
        )

        url = CROSSREF_JOURNAL_WORKS.format(issn=issn)
        rows = settings.crossref_rows
        entries: list[dict[str, Any]] = []
        skipped = 0

        for page in range(settings.crossref_max_pages):
            result, items = await self._fetch_page(url, filter_value, rows, page * rows)
            if result is not None:
                return result

            for message in items:
                if message.get("type") and message["type"] not in CROSSREF_KEEP_TYPES:
                    skipped += 1
                    continue
                entry = work_to_entry(message)
                if entry is None:
                    skipped += 1
                    continue
                entries.append(entry)

            if len(items) < rows:
                break

        if skipped:
            log.debug(f"Crossref {issn}: {skipped} itens descartados (tipo ou metadados)")

        return FetchResult(
            status=FetchStatus.OK,
            text=json.dumps({"entries": entries}),
        )

    async def _fetch_page(
        self, url: str, filter_value: str, rows: int, offset: int
    ) -> tuple[FetchResult | None, list[dict[str, Any]]]:
        """Busca uma página. Retorna ``(erro, [])`` em falha ou ``(None, items)``."""
        params = self._params(
            select=CROSSREF_SELECT,
            filter=filter_value,
            sort="published",
            order="desc",
            rows=rows,
            offset=offset,
        )

        try:
            response = await self.client.get(url, params=params)
        except httpx.HTTPError as e:
            return (
                FetchResult(status=FetchStatus.TRANSIENT_ERROR, error=f"Erro de rede: {e}"),
                [],
            )

        if response.status_code == 429:
            # Limite de taxa: é falha da nossa cadência, não da fonte — entra
            # como transitório para não punir o feed com error_count.
            return (
                FetchResult(
                    status=FetchStatus.TRANSIENT_ERROR,
                    error="HTTP 429 (limite de taxa do Crossref)",
                ),
                [],
            )
        if response.status_code >= 500:
            return (
                FetchResult(
                    status=FetchStatus.TRANSIENT_ERROR, error=f"HTTP {response.status_code}"
                ),
                [],
            )
        if response.status_code >= 400:
            # 404 é ISSN inexistente; 400 é parâmetro inválido do nosso lado
            # (ex.: um `select` que a rota não aceita). Ambos são permanentes e
            # acionáveis, e não "bloqueio" — tratar 400 como BLOCKED faria um
            # bug nosso parecer um WAF da editora e esconderia a causa.
            return (
                FetchResult(
                    status=FetchStatus.INVALID_CONTENT,
                    error=self._describe_error(response),
                ),
                [],
            )

        try:
            payload = response.json()
            items = payload["message"]["items"]
        except Exception as e:
            return (
                FetchResult(
                    status=FetchStatus.INVALID_CONTENT,
                    error=f"Resposta do Crossref não é JSON de works: {e}",
                ),
                [],
            )

        if not isinstance(items, list):
            return (
                FetchResult(
                    status=FetchStatus.INVALID_CONTENT,
                    error="Resposta do Crossref sem lista de items",
                ),
                [],
            )

        return None, items

    @staticmethod
    def _describe_error(response: httpx.Response) -> str:
        """Extrai a mensagem de validação do Crossref, quando houver.

        O Crossref devolve ``{"status":"failed","message":[{"message": "..."}]}``
        em erros de parâmetro. Propagar essa mensagem é o que transforma "HTTP
        400" em algo diagnosticável no ``last_error`` do feed.
        """
        detail = response.text or ""
        try:
            payload = response.json()
            message = payload.get("message")
            if isinstance(message, list) and message:
                detail = message[0].get("message") or detail
            elif isinstance(message, str):
                detail = message
        except Exception:
            pass
        detail = re.sub(r"\s+", " ", str(detail)).strip()[:200]
        return (
            f"HTTP {response.status_code}: {detail}" if detail else f"HTTP {response.status_code}"
        )

    async def validate_issn(self, issn: str) -> tuple[bool, str | None]:
        """Confirma que o ISSN existe no Crossref e retorna o título registrado.

        Uso em curadoria (``scripts/validate_journal_issn.py``) e no endpoint de
        teste de feed: cadastrar um ISSN errado gera um feed silenciosamente
        vazio, que é exatamente o modo de falha que o ADR-0006 combate.
        """
        try:
            response = await self.client.get(
                CROSSREF_JOURNAL.format(issn=issn), params=self._params()
            )
        except httpx.HTTPError as e:
            return False, f"Erro de rede: {e}"

        if response.status_code in (404, 410):
            return False, f"ISSN {issn} não encontrado no Crossref"
        if response.status_code >= 400:
            return False, self._describe_error(response)

        try:
            message = response.json()["message"]
        except Exception as e:
            return False, f"Resposta inválida do Crossref: {e}"

        title = (message.get("title") or "").strip()
        return True, title or None
