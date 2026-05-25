#!/usr/bin/env python3
"""
Script para reclassificar artigos que podem estar classificados incorretamente.
Usa o sistema de classificação atualizado com categorias mais precisas.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models import Article, Category
from app.ai.manager import AIManager
from app.services.classification_service import ClassificationService


async def get_articles_to_reclassify(db: AsyncSession) -> list[Article]:
    """Busca artigos que podem precisar de reclassificação."""
    # Buscar artigos classificados como "clinica" que podem ser sobre autismo ou notícias
    result = await db.execute(
        select(Article)
        .join(Category, Article.category_id == Category.id)
        .where(Category.slug == "clinica")
        .order_by(Article.id.desc())
    )
    return list(result.scalars().all())


async def reclassify_article(
    db: AsyncSession,
    article: Article,
    ai_manager: AIManager,
) -> tuple[str, str, float]:
    """
    Reclassifica um artigo e retorna (categoria_antiga, categoria_nova, confiança).
    """
    # Construir texto para classificação
    text_parts = []
    if article.title:
        text_parts.append(article.title)
    if article.title_translated:
        text_parts.append(article.title_translated)
    if article.abstract:
        text_parts.append(article.abstract)
    if article.abstract_translated:
        text_parts.append(article.abstract_translated)
    if article.keywords:
        text_parts.append(article.keywords)

    classification_text = " ".join(text_parts)

    if not classification_text.strip():
        return (article.category.slug if article.category else "outros", "outros", 0.0)

    # Classificar usando o sistema atualizado
    category_slugs_with_confidence = await ClassificationService.classify_with_multiple_categories(
        db=db,
        text=classification_text,
        ai_manager=ai_manager,
        min_confidence=0.3,
    )

    if not category_slugs_with_confidence:
        return (article.category.slug if article.category else "outros", "outros", 0.0)

    new_slug, confidence = category_slugs_with_confidence[0]
    old_slug = article.category.slug if article.category else "outros"

    return (old_slug, new_slug, confidence)


async def update_article_category(
    db: AsyncSession,
    article: Article,
    new_slug: str,
    confidence: float,
) -> bool:
    """Atualiza a categoria do artigo."""
    # Buscar nova categoria
    result = await db.execute(
        select(Category).where(Category.slug == new_slug)
    )
    new_category = result.scalar_one_or_none()

    if not new_category:
        print(f"  ⚠️  Categoria '{new_slug}' não encontrada!")
        return False

    # Atualizar artigo
    article.category_id = new_category.id
    article.classification_confidence = confidence

    await db.commit()
    return True


async def main():
    """Função principal."""
    print("=" * 70)
    print("🔄 RECLASSIFICAÇÃO DE ARTIGOS")
    print("=" * 70)
    print()

    async with async_session_maker() as db:
        # Inicializar AI Manager
        ai_manager = AIManager()
        print(f"📊 Provedores de IA configurados: {list(ai_manager.providers.keys())}")
        print()

        # Buscar artigos para reclassificar
        articles = await get_articles_to_reclassify(db)
        print(f"📝 Encontrados {len(articles)} artigos classificados como 'clinica'")
        print()

        if not articles:
            print("✅ Nenhum artigo para reclassificar!")
            return

        # Confirmar
        confirm = input("Deseja continuar com a reclassificação? (s/N): ").strip().lower()
        if confirm != "s":
            print("Operação cancelada.")
            return

        print()
        print("-" * 70)

        changed = 0
        kept = 0

        for article in articles:
            print(f"\n📄 Artigo #{article.id}: {article.title[:60]}...")

            old_slug, new_slug, confidence = await reclassify_article(db, article, ai_manager)

            if old_slug != new_slug:
                print(f"   🔄 {old_slug} → {new_slug} (confiança: {confidence:.2f})")

                # Perguntar se quer atualizar
                update = input("   Atualizar? (s/N): ").strip().lower()
                if update == "s":
                    if await update_article_category(db, article, new_slug, confidence):
                        print("   ✅ Atualizado!")
                        changed += 1
                    else:
                        print("   ❌ Falha ao atualizar")
                        kept += 1
                else:
                    print("   ⏭️  Mantido")
                    kept += 1
            else:
                print(f"   ✓ Mantém: {old_slug} (confiança: {confidence:.2f})")
                kept += 1

        print()
        print("=" * 70)
        print(f"📊 RESUMO: {changed} alterados, {kept} mantidos")
        print("=" * 70)


async def batch_reclassify():
    """Reclassifica todos os artigos automaticamente (sem confirmação individual)."""
    print("=" * 70)
    print("🔄 RECLASSIFICAÇÃO AUTOMÁTICA DE ARTIGOS")
    print("=" * 70)
    print()

    async with async_session_maker() as db:
        # Inicializar AI Manager
        ai_manager = AIManager()
        print(f"📊 Provedores de IA configurados: {list(ai_manager.providers.keys())}")
        print()

        # Buscar artigos para reclassificar
        articles = await get_articles_to_reclassify(db)
        print(f"📝 Encontrados {len(articles)} artigos classificados como 'clinica'")
        print()

        if not articles:
            print("✅ Nenhum artigo para reclassificar!")
            return

        changed = 0
        kept = 0
        errors = 0

        for i, article in enumerate(articles, 1):
            print(f"[{i}/{len(articles)}] Artigo #{article.id}: {article.title[:50]}...", end=" ")

            try:
                old_slug, new_slug, confidence = await reclassify_article(db, article, ai_manager)

                if old_slug != new_slug and confidence >= 0.5:
                    if await update_article_category(db, article, new_slug, confidence):
                        print(f"✅ {old_slug} → {new_slug}")
                        changed += 1
                    else:
                        print(f"❌ Erro")
                        errors += 1
                else:
                    print(f"⏭️ Mantém {old_slug}")
                    kept += 1
            except Exception as e:
                print(f"❌ Erro: {e}")
                errors += 1

        print()
        print("=" * 70)
        print(f"📊 RESUMO: {changed} alterados, {kept} mantidos, {errors} erros")
        print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reclassifica artigos")
    parser.add_argument("--batch", action="store_true", help="Modo batch (sem confirmação)")
    args = parser.parse_args()

    if args.batch:
        asyncio.run(batch_reclassify())
    else:
        asyncio.run(main())
