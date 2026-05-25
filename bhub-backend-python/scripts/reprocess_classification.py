"""
Script para reclassificar artigos existentes usando o sistema de classificação.
Suporta múltiplas categorias e criação automática quando necessário.
"""

import asyncio
import os
import sys

# Configurar path antes de qualquer import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Forçar API key do ambiente
os.environ.setdefault("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))

from sqlalchemy import select, delete

from app.config import settings
from app.database import get_session_context, init_db
from app.models import Article, Category, article_categories
from app.ai import get_ai_manager
from app.core.logging import setup_logging, log

# Import opcional do ImpactRatingService
try:
    from app.ml.impact_rating import ImpactRatingService
except ImportError:
    ImpactRatingService = None


async def get_or_create_category(db, slug: str, name: str = None) -> Category:
    """Obtém ou cria uma categoria pelo slug."""
    result = await db.execute(select(Category).where(Category.slug == slug))
    category = result.scalar_one_or_none()

    if category is None:
        # Criar nova categoria
        category = Category(
            slug=slug,
            name=name or slug.replace("-", " ").title(),
            description=f"Categoria criada automaticamente: {slug}",
            keywords=slug,
        )
        db.add(category)
        await db.flush()
        log.info(f"Nova categoria criada: {category.name}")

    return category


async def reprocess_classification():
    """Função principal de reprocessamento."""
    setup_logging()

    log.info("=" * 60)
    log.info("RECLASSIFICAÇÃO DE ARTIGOS")
    log.info("=" * 60)

    # Inicializar banco
    log.info("Inicializando banco de dados...")
    await init_db()

    # Configurar AI Manager
    log.info("Configurando AI Manager...")
    ai_manager = get_ai_manager()
    ai_manager._setup_providers()

    providers = list(ai_manager.providers.keys())
    log.info(f"Provedores disponíveis: {providers}")

    if not providers:
        log.error("Nenhum provedor de IA configurado!")
        log.error("Verifique se DEEPSEEK_API_KEY está no .env")
        return

    async with get_session_context() as db:
        # Garantir categorias padrão
        from app.models import DEFAULT_CATEGORIES

        result = await db.execute(select(Category))
        existing_cats = {c.slug: c for c in result.scalars().all()}

        for cat_data in DEFAULT_CATEGORIES:
            if cat_data["slug"] not in existing_cats:
                log.info(f"Criando categoria padrão: {cat_data['name']}")
                db.add(Category(**cat_data))

        await db.commit()

        # Recarregar categorias
        result = await db.execute(select(Category))
        categories_map = {c.slug: c.id for c in result.scalars().all()}
        log.info(f"Categorias disponíveis: {list(categories_map.keys())}")

        # Buscar artigos (limitar para teste)
        limit = int(os.getenv("REPROCESS_LIMIT", "10"))
        result = await db.execute(select(Article).limit(limit))
        articles = result.scalars().all()

        log.info(f"Processando {len(articles)} artigos...")
        log.info("")

        processed = 0
        updated = 0
        errors = 0

        for article in articles:
            processed += 1
            title_preview = article.title[:50] if article.title else "Sem título"
            log.info(f"[{processed}/{len(articles)}] {title_preview}...")

            try:
                # Preparar texto
                text_parts = [article.title or ""]
                if article.abstract:
                    text_parts.append(article.abstract)
                if article.keywords:
                    text_parts.append(article.keywords)

                text = " ".join(text_parts).strip()

                if not text:
                    log.warning(f"  -> Artigo sem texto para classificar")
                    continue

                # Classificar usando AI Manager
                log.info(f"  -> Classificando...")
                category_slug, confidence, provider = await ai_manager.classify(text)
                log.info(f"  -> Resultado: {category_slug} ({confidence:.2f}) via {provider}")

                if category_slug and category_slug != "outros":
                    # Verificar se categoria existe
                    if category_slug not in categories_map:
                        # Criar categoria automaticamente
                        cat = await get_or_create_category(db, category_slug)
                        categories_map[category_slug] = cat.id

                    cat_id = categories_map[category_slug]

                    # Remover associações antigas
                    await db.execute(
                        delete(article_categories).where(
                            article_categories.c.article_id == article.id
                        )
                    )

                    # Criar nova associação na tabela many-to-many
                    from sqlalchemy import insert
                    await db.execute(
                        insert(article_categories).values(
                            article_id=article.id,
                            category_id=cat_id,
                            confidence=confidence,
                            is_primary=True,
                            auto_created=False,
                        )
                    )

                    # Atualizar referência principal
                    article.category_id = cat_id
                    article.classification_confidence = confidence

                    updated += 1
                    log.info(f"  -> Atualizado: {category_slug}")

                    # Calcular impact_score se disponível
                    if ImpactRatingService and article.impact_score is None:
                        try:
                            impact = await ImpactRatingService.calculate_impact(
                                title=article.title,
                                abstract=article.abstract,
                                keywords=article.keywords,
                                journal_name=article.journal_name,
                                has_doi=bool(article.doi),
                            )
                            article.impact_score = impact
                            log.info(f"  -> Impact score: {impact:.2f}")
                        except Exception as e:
                            log.debug(f"  -> Erro ao calcular impact: {e}")
                else:
                    log.info(f"  -> Mantido como: {article.category_id or 'sem categoria'}")

            except Exception as e:
                log.error(f"  -> ERRO: {e}")
                import traceback
                log.debug(traceback.format_exc())
                errors += 1

            # Commit a cada artigo para não perder progresso
            await db.commit()

            # Rate limiting
            await asyncio.sleep(0.5)

        log.info("")
        log.info("=" * 60)
        log.info("RESUMO")
        log.info(f"  Processados: {processed}")
        log.info(f"  Atualizados: {updated}")
        log.info(f"  Erros: {errors}")
        log.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(reprocess_classification())
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
    except Exception as e:
        print(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
