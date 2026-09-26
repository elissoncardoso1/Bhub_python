"""Cadastra os feeds de periódicos científicos.

Duas vias de ingestão (ver ``docs/adr/0007-crossref-para-periodicos.md``):

- ``CROSSREF``: periódicos de editoras que servem o RSS atrás de anti-bot
  (Wiley, Taylor & Francis, Springer). A fonte é a API REST do Crossref,
  consultada por ISSN. Para esses, ``feed_url`` é o endpoint do Crossref que o
  sync realmente usa e ``website_url`` é a página do periódico para humanos.
- ``RSS``: periódicos cujo feed da editora funciona (OJS, WordPress).

O script é **idempotente**: casa o registro existente por ``issn`` (feeds do
Crossref) ou por ``feed_url`` (feeds RSS) e atualiza o que estiver defasado.
É essa atualização que corrige o defeito D3 do incidente de 2026-09-22 — o
script antigo só inseria, então a URL morta da Revista Perspectivas continuava
sendo recriada numa instalação limpa.

Os ISSNs eletrônicos abaixo foram validados ao vivo contra o Crossref em
2026-09-25 (``scripts/validate_journal_issn.py``); os títulos conferem.
"""

import asyncio

from sqlalchemy import select

from app.database import get_session_context
from app.models import Feed, FeedJournalSource, FeedType, SyncFrequency


def _crossref_feed_url(issn: str) -> str:
    """Endpoint do Crossref usado como ``feed_url`` de um periódico migrado."""
    return f"https://api.crossref.org/journals/{issn}/works"


JOURNAL_FEEDS = [
    # --- Português (OJS/WordPress funcionando) -----------------------------
    {
        "name": "Revista Perspectivas",
        "journal_name": "Revista Perspectivas em Análise do Comportamento",
        # URL OJS (gateway WebFeed). A forma antiga `.../perspectivas/feed`
        # respondia 404 e era recriada por este script (D3).
        "feed_url": (
            "https://revistaperspectivas.org/perspectivas/gateway/plugin/WebFeedGatewayPlugin/rss2"
        ),
        "website_url": "https://revistaperspectivas.org",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
    },
    {
        "name": "Revista ESPECTRO",
        "journal_name": "Revista ESPECTRO",
        "feed_url": (
            "https://espectro.ufscar.br/index.php/1979/gateway/plugin/WebFeedGatewayPlugin/rss2"
        ),
        "website_url": "https://espectro.ufscar.br",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
    },
    {
        "name": "Boletim Contexto",
        "journal_name": "Boletim Contexto",
        "feed_url": "https://boletimcontexto.wordpress.com/feed",
        "website_url": "https://boletimcontexto.wordpress.com",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
    },
    # --- Wiley (RSS responde 403) -> Crossref ------------------------------
    {
        "name": "JABA",
        "journal_name": "Journal of Applied Behavior Analysis",
        "issn": "1938-3703",
        "website_url": "https://onlinelibrary.wiley.com/journal/19383703",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    {
        "name": "JEAB",
        "journal_name": "Journal of the Experimental Analysis of Behavior",
        "issn": "1938-3711",
        "website_url": "https://onlinelibrary.wiley.com/journal/19383711",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    # --- Taylor & Francis (RSS responde 403) -> Crossref -------------------
    {
        "name": "JOBM",
        "journal_name": "Journal of Organizational Behavior Management",
        "issn": "1540-8604",
        "website_url": "https://www.tandfonline.com/journals/worg20",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    # --- Springer (RSS responde 200 com challenge anti-bot) -> Crossref ----
    {
        "name": "BAP",
        "journal_name": "Behavior Analysis in Practice",
        "issn": "2196-8934",
        "website_url": "https://link.springer.com/journal/40617",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    {
        "name": "Perspectives on Behavior Science",
        "journal_name": "Perspectives on Behavior Science",
        "issn": "2520-8977",
        "website_url": "https://link.springer.com/journal/40614",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    {
        "name": "The Analysis of Verbal Behavior",
        "journal_name": "The Analysis of Verbal Behavior",
        "issn": "2196-8926",
        "website_url": "https://link.springer.com/journal/40616",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    {
        "name": "Behavior and Social Issues",
        "journal_name": "Behavior and Social Issues",
        "issn": "2376-6786",
        "website_url": "https://link.springer.com/journal/42822",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.CROSSREF,
    },
    # --- Morto ------------------------------------------------------------
    {
        # Sem publicação desde 2024; o conteúdo de OBM já é coberto pelo JOBM.
        "name": "OBM Network News",
        "journal_name": "OBM Network News",
        "feed_url": "https://www.obmnetwork.com/news/news_rss.asp",
        "website_url": "https://www.obmnetwork.com/news/",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
        "is_active": False,
    },
]


async def _find_existing(session, feed_data: dict) -> Feed | None:
    """Localiza o feed existente pelo ISSN (Crossref) ou pela URL (RSS)."""
    issn = feed_data.get("issn")
    if issn:
        result = await session.execute(select(Feed).where(Feed.issn == issn))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

    feed_url = feed_data.get("feed_url")
    if feed_url:
        result = await session.execute(select(Feed).where(Feed.feed_url == feed_url))
        return result.scalar_one_or_none()

    return None


async def add_feeds() -> None:
    """Insere feeds novos e corrige os defasados (idempotente)."""
    async with get_session_context() as session:
        added = 0
        updated = 0

        for feed_data in JOURNAL_FEEDS:
            is_crossref = feed_data["journal_source"] is FeedJournalSource.CROSSREF
            issn = feed_data.get("issn")
            # Para o Crossref a URL de trabalho é o endpoint da API; para RSS é
            # a URL declarada no próprio dado.
            feed_url = _crossref_feed_url(issn) if is_crossref else feed_data["feed_url"]

            existing = await _find_existing(session, feed_data)

            if existing is None:
                session.add(
                    Feed(
                        name=feed_data["name"],
                        journal_name=feed_data["journal_name"],
                        feed_url=feed_url,
                        website_url=feed_data["website_url"],
                        feed_type=feed_data["feed_type"],
                        journal_source=feed_data["journal_source"],
                        issn=issn,
                        is_active=feed_data.get("is_active", True),
                        sync_frequency=SyncFrequency.DAILY,
                    )
                )
                added += 1
                print(f"Adicionado: {feed_data['name']}")
                continue

            changes: list[str] = []
            desired = {
                "name": feed_data["name"],
                "journal_name": feed_data["journal_name"],
                "website_url": feed_data["website_url"],
                "feed_url": feed_url,
                "journal_source": feed_data["journal_source"],
                "issn": issn,
            }
            for field, value in desired.items():
                if value is not None and getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changes.append(field)

            # Um feed migrado para o Crossref não deve carregar os validadores
            # de cache do feed antigo: o Crossref não usa ETag/Last-Modified, e
            # um If-None-Match herdado não é enviado a ele de qualquer forma.
            if is_crossref and (existing.http_etag or existing.http_last_modified):
                existing.http_etag = None
                existing.http_last_modified = None
                changes.append("http_cache")

            # Migração de via de ingestão zera os erros acumulados: o
            # error_count era da fonte antiga (RSS bloqueado) e não descreve a
            # nova. Sem isso o feed nasce com error_count=16 contra max_errors=5.
            if is_crossref and existing.error_count:
                existing.error_count = 0
                existing.last_error = None
                changes.append("error_count")

            if changes:
                updated += 1
                print(f"Atualizado: {feed_data['name']} ({', '.join(changes)})")

        await session.commit()
        print(
            f"{len(JOURNAL_FEEDS)} periódicos processados: "
            f"{added} adicionados, {updated} atualizados."
        )


if __name__ == "__main__":
    asyncio.run(add_feeds())
