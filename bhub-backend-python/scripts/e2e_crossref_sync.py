"""Teste ponta a ponta: sync de um feed Crossref contra banco real + API real.

Não é teste automatizado (usa rede e um Postgres real). Roda manualmente para
validar o pipeline completo antes de um deploy:

    docker run --rm --network <net> -v "$PWD:/app" -w /app \
      -e DATABASE_URL='postgresql+asyncpg://...' \
      --entrypoint python bhub-backend-python-backend:latest scripts/e2e_crossref_sync.py

Faz exatamente o que o scheduler fará: cria o feed, chama `sync_feed` e confere
os artigos gravados. Termina removendo o que criou para poder rodar de novo.
"""

import asyncio
import sys

from sqlalchemy import delete, func, select

from app.database import get_session_context
from app.models import Article, Feed, FeedJournalSource, FeedType, SyncFrequency
from app.services.feed_aggregator import FeedAggregatorService

ISSN = "2196-8934"  # Behavior Analysis in Practice
FEED_URL = f"https://api.crossref.org/journals/{ISSN}/works"


async def cleanup() -> None:
    """Remove artigos e feed criados pelo teste (idempotência entre execuções)."""
    async with get_session_context() as session:
        result = await session.execute(select(Feed).where(Feed.issn == ISSN))
        feed = result.scalar_one_or_none()
        if feed is None:
            return
        # A FK exige remover os artigos antes do feed.
        await session.execute(delete(Article).where(Article.feed_id == feed.id))
        await session.execute(delete(Feed).where(Feed.id == feed.id))
        await session.commit()


async def main() -> int:
    await cleanup()

    async with get_session_context() as session:
        feed = Feed(
            name="E2E BAP",
            journal_name="Behavior Analysis in Practice",
            feed_url=FEED_URL,
            website_url="https://link.springer.com/journal/40617",
            feed_type=FeedType.RSS,
            journal_source=FeedJournalSource.CROSSREF,
            issn=ISSN,
            is_active=True,
            sync_frequency=SyncFrequency.DAILY,
        )
        session.add(feed)
        await session.commit()
        await session.refresh(feed)
        feed_id = feed.id
        print(f"Feed criado: id={feed_id} ISSN={ISSN} source={feed.journal_source}")

    async with get_session_context() as session:
        service = FeedAggregatorService(session)
        try:
            result = await service.sync_feed(feed_id)
        finally:
            await service.close()

    print(
        f"\nresultado: success={result.success} new_articles={result.new_articles} "
        f"duration={result.duration_seconds:.1f}s errors={result.errors}"
    )

    async with get_session_context() as session:
        feed = (await session.execute(select(Feed).where(Feed.id == feed_id))).scalar_one()
        print(
            f"\nfeed: error_count={feed.error_count} last_error={feed.last_error!r} "
            f"total_articles={feed.total_articles} last_success={feed.last_successful_sync_at}"
        )

        total = await session.scalar(
            select(func.count()).select_from(Article).where(Article.feed_id == feed_id)
        )
        print(f"artigos gravados: {total}")

        sample = (
            (await session.execute(select(Article).where(Article.feed_id == feed_id).limit(3)))
            .scalars()
            .all()
        )

        for article in sample:
            print("  ---")
            print(f"  doi      : {article.doi}")
            print(f"  title    : {article.title[:70]}")
            print(f"  date     : {article.publication_date}")
            print(f"  journal  : {article.journal_name}")
            print(f"  language : {article.language}")
            print(f"  url      : {article.original_url}")
            print(f"  pdf_url  : {article.pdf_url}")
            print(f"  open_acc : {article.is_open_access}")
            print(f"  abstract : {(article.abstract or '')[:70]}")
            print(f"  authors  : {article.authors_str[:70]}")

        # Deduplicação: um segundo sync não pode duplicar.
        before = total
        service = FeedAggregatorService(session)
        try:
            second = await service.sync_feed(feed_id)
        finally:
            await service.close()

        after = await session.scalar(
            select(func.count()).select_from(Article).where(Article.feed_id == feed_id)
        )
        print(
            f"\n2o sync: new_articles={second.new_articles} "
            f"artigos antes={before} depois={after} (devem ser iguais)"
        )

        ok = second.new_articles == 0 and before == after and before > 0

    await cleanup()
    print(f"\nlimpeza concluída. Verdicto: {'OK' if ok else 'FALHOU'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
