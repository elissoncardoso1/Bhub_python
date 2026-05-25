"""
Script de teste rápido para verificar se a classificação está funcionando.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.database import get_session_context, init_db
from app.models import Article
from app.ai import get_ai_manager
from app.core.logging import setup_logging, log

# Import direto
import importlib.util
spec = importlib.util.spec_from_file_location(
    "classification_service",
    Path(__file__).parent.parent / "app" / "services" / "classification_service.py"
)
classification_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classification_module)
ClassificationService = classification_module.ClassificationService

async def test_classification():
    setup_logging()
    log.info("Teste de classificação...")

    await init_db()

    ai_manager = get_ai_manager()
    ai_manager._setup_providers()
    log.info(f"Provedores: {list(ai_manager.providers.keys())}")

    async with get_session_context() as db:
        # Pegar apenas 1 artigo para teste
        from sqlalchemy import select
        result = await db.execute(select(Article).limit(1))
        article = result.scalar_one_or_none()

        if not article:
            log.error("Nenhum artigo encontrado no banco")
            return

        log.info(f"Testando com artigo: {article.title[:50]}...")

        text = f"{article.title} {article.abstract or ''} {article.keywords or ''}"

        log.info("Chamando classify_with_multiple_categories...")
        categories = await ClassificationService.classify_with_multiple_categories(
            db=db,
            text=text,
            ai_manager=ai_manager,
            min_confidence=0.3,
        )

        log.info(f"Resultado: {categories}")

        if categories:
            log.info("Atribuindo categorias...")
            assigned = await ClassificationService.assign_categories_to_article(
                db=db,
                article_id=article.id,
                category_slugs_with_confidence=categories,
                auto_create=True,
            )
            log.info(f"Categorias atribuídas: {[c.name for c in assigned]}")
            await db.commit()

if __name__ == "__main__":
    asyncio.run(test_classification())
