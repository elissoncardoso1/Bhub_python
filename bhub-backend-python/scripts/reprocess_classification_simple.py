"""
Script simplificado para reclassificar artigos usando classificação única (mais rápido).
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import select, delete

sys.path.insert(0, ".")
load_dotenv()

from app.config import settings
settings.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

from app.database import get_session_context, init_db
from app.models import Article, Category, article_categories
from app.ai import get_ai_manager
from app.core.logging import setup_logging, log

async def reprocess_classification_simple():
    setup_logging()
    log.info("=" * 60)
    log.info("RECLASSIFICAÇÃO SIMPLIFICADA DE ARTIGOS")
    log.info("=" * 60)

    log.info("Inicializando banco...")
    await init_db()

    log.info("Configurando AI Manager...")
    ai_manager = get_ai_manager()
    ai_manager._setup_providers()
    log.info(f"Provedores: {list(ai_manager.providers.keys())}")

    if not ai_manager.providers:
        log.error("Nenhum provedor de IA configurado.")
        return

    async with get_session_context() as db:
        # Garantir categorias padrão
        from app.models import DEFAULT_CATEGORIES
        result = await db.execute(select(Category))
        existing_cats = {c.slug: c for c in result.scalars().all()}

        for cat_data in DEFAULT_CATEGORIES:
            if cat_data["slug"] not in existing_cats:
                new_cat = Category(**cat_data)
                db.add(new_cat)

        await db.commit()

        # Recarregar mapeamento
        result = await db.execute(select(Category))
        categories = {c.slug: c.id for c in result.scalars().all()}

        # Buscar artigos (limitar para teste)
        result = await db.execute(select(Article).limit(5))
        articles = result.scalars().all()

        log.info(f"Processando {len(articles)} artigos...")

        processed = 0
        updated = 0

        for article in articles:
            processed += 1
            log.info(f"\n[{processed}/{len(articles)}] {article.title[:50]}...")

            try:
                text = f"{article.title} {article.abstract or ''} {article.keywords or ''}"

                # Classificação simples (única categoria)
                log.info("  -> Classificando...")
                category_slug, confidence, provider = await ai_manager.classify(text)
                log.info(f"  -> Resultado: {category_slug} ({confidence:.2f}) via {provider}")

                if category_slug and category_slug != "outros":
                    cat_id = categories.get(category_slug)

                    if cat_id:
                        # Remover associações antigas
                        await db.execute(
                            delete(article_categories).where(article_categories.c.article_id == article.id)
                        )

                        # Criar nova associação
                        from sqlalchemy.dialects.postgresql import insert
                        await db.execute(
                            insert(article_categories).values(
                                article_id=article.id,
                                category_id=cat_id,
                                confidence=confidence,
                                is_primary=True,
                                auto_created=False,
                            )
                        )

                        # Atualizar category_id primário
                        article.category_id = cat_id
                        article.classification_confidence = confidence

                        updated += 1
                        log.info(f"  -> ✓ Atualizado")
                    else:
                        log.warning(f"  -> Categoria '{category_slug}' não encontrada")

            except Exception as e:
                log.error(f"  -> Erro: {e}")
                import traceback
                log.error(traceback.format_exc())

            # Commit a cada artigo
            await db.commit()
            await asyncio.sleep(0.5)

        log.info("\n" + "=" * 60)
        log.info(f"Processados: {processed}, Atualizados: {updated}")
        log.info("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(reprocess_classification_simple())
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
    except Exception as e:
        log.error(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
