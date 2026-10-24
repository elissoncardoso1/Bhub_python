"""Testa o script de conversão de produção contra um banco com dados reais.

Não é teste automatizado. Cria feeds com os mesmos nomes/estados do incidente de
2026-09-22 e verifica que `migrate_journal_feeds_to_crossref.py` os converte
corretamente, incluindo o rollback do dry-run.

    docker run --rm --network <net> -v "$PWD:/app" -w /app \
      -e DATABASE_URL='postgresql+asyncpg://...' \
      --entrypoint python bhub-backend-python-backend:latest \
      scripts/e2e_migration.py
"""

import asyncio
import sys

from sqlalchemy import delete, select

from app.database import get_session_context
from app.models import Feed, FeedJournalSource, FeedType, SyncFrequency

# Reproduz o estado real do incidente: JABA nunca sincronizou (error_count=16),
# BAP sincronizava de mentira (error_count=0 e sucesso de hoje, parado desde
# 2026-08-04) e o OBM está morto desde 2024.
SEEDS = [
    {
        "name": "JABA",
        "journal_name": "Journal of Applied Behavior Analysis",
        "feed_url": "https://onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)1938-3703",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
        "error_count": 16,
        "last_error": "HTTP 403 (impersonado)",
        "http_etag": '"etag-antigo"',
    },
    {
        "name": "BAP",
        "journal_name": "Behavior Analysis in Practice",
        "feed_url": "https://link.springer.com/search.rss?facet-journal-id=40617",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
        "error_count": 0,
        "total_articles": 36,
    },
    {
        "name": "OBM Network News",
        "journal_name": "OBM Network News",
        "feed_url": "https://www.obmnetwork.com/news/news_rss.asp",
        "feed_type": FeedType.RSS,
        "journal_source": FeedJournalSource.RSS,
        "error_count": 0,
    },
]


async def cleanup() -> None:
    names = [seed["name"] for seed in SEEDS]
    async with get_session_context() as session:
        await session.execute(delete(Feed).where(Feed.name.in_(names)))
        await session.commit()


async def seed() -> None:
    async with get_session_context() as session:
        for data in SEEDS:
            session.add(
                Feed(
                    sync_frequency=SyncFrequency.DAILY,
                    is_active=True,
                    **data,
                )
            )
        await session.commit()


async def snapshot() -> dict[str, dict]:
    async with get_session_context() as session:
        result = await session.execute(
            select(Feed).where(Feed.name.in_([s["name"] for s in SEEDS]))
        )
        return {
            feed.name: {
                "source": feed.journal_source.value,
                "issn": feed.issn,
                "url": feed.feed_url,
                "active": feed.is_active,
                "errors": feed.error_count,
                "etag": feed.http_etag,
            }
            for feed in result.scalars().all()
        }


async def main() -> int:
    from scripts.migrate_journal_feeds_to_crossref import migrate

    await cleanup()
    await seed()
    print("=== estado inicial ===")
    for name, row in (await snapshot()).items():
        print(f"  {name:<20} {row}")

    print("\n=== DRY-RUN ===")
    await migrate(apply=False)
    after_dry = await snapshot()
    jaba = after_dry["JABA"]
    dry_ok = jaba["source"] == "RSS" and jaba["issn"] is None and jaba["errors"] == 16
    print(f"  dry-run não alterou nada? {dry_ok}")

    print("\n=== APPLY ===")
    await migrate(apply=True)
    after = await snapshot()
    for name, row in after.items():
        print(f"  {name:<20} {row}")

    jaba = after["JABA"]
    bap = after["BAP"]
    obm = after["OBM Network News"]

    checks = {
        "JABA migrado para Crossref": jaba["source"] == "CROSSREF",
        "JABA com ISSN correto": jaba["issn"] == "1938-3703",
        "JABA error_count zerado": jaba["errors"] == 0,
        "JABA sem etag herdado": jaba["etag"] is None,
        "JABA url virou endpoint Crossref": jaba["url"].startswith("https://api.crossref.org/"),
        "BAP migrado para Crossref": bap["source"] == "CROSSREF",
        "BAP com ISSN correto": bap["issn"] == "2196-8934",
        "OBM desativado": obm["active"] is False,
        "OBM permanece RSS": obm["source"] == "RSS",
    }

    print()
    ok = True
    for label, passed in checks.items():
        print(f"  [{'OK' if passed else 'FALHOU'}] {label}")
        ok = ok and passed and dry_ok

    # Idempotência: aplicar de novo não deve mudar nada.
    print("\n=== APPLY novamente (idempotência) ===")
    await migrate(apply=True)
    again = await snapshot()
    idempotent = again == after
    print(f"  estado inalterado? {idempotent}")
    ok = ok and idempotent

    await cleanup()
    print(f"\nlimpeza concluída. Verdicto: {'OK' if ok else 'FALHOU'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
