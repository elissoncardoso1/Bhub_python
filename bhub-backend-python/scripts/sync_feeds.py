"""
Script para sincronizar todos os feeds RSS.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from app.core.logging import setup_logging, log
from app.database import get_session_context, init_db
from app.services import FeedAggregatorService


async def sync_all_feeds():
    """Sincroniza todos os feeds ativos."""
    setup_logging()
    log.info("=" * 60)
    log.info("Iniciando sincronização de todos os feeds...")
    log.info("=" * 60)

    await init_db()
    log.info("✓ Banco de dados inicializado")

    async with get_session_context() as db:
        service = FeedAggregatorService(db)

        try:
            result = await service.sync_all_active_feeds()

            log.info("")
            log.info("=" * 60)
            log.info("RESUMO DA SINCRONIZAÇÃO")
            log.info("=" * 60)
            log.info(f"  Feeds sincronizados: {result.total_feeds}")
            log.info(f"  Artigos novos: {result.new_articles}")
            errors = []
            if hasattr(result, "results") and result.results:
                for item in result.results:
                    if getattr(item, "errors", None):
                        errors.extend(item.errors)

            log.info(f"  Erros: {len(errors)}")
            if errors:
                log.warning("Erros encontrados:")
                for error in errors:
                    log.warning(f"  - {error}")

            log.info("=" * 60)

        finally:
            await service.close()


if __name__ == "__main__":
    try:
        asyncio.run(sync_all_feeds())
    except Exception as e:
        log.error(f"Erro ao executar sync: {e}", exc_info=True)
        sys.exit(1)
