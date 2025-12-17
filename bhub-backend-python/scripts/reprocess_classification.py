"""
Script para reclassificar artigos existentes usando DeepSeek AI.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import select, update

sys.path.insert(0, ".")
load_dotenv()

from app.config import settings
# Force reload of settings to ensure API key is present if it was just added
settings.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

from app.database import get_session_context, init_db
from app.models import Article, Category
from app.ai import get_ai_manager
from app.core.logging import setup_logging, log

async def reprocess_classification():
    setup_logging()
    log.info("=" * 60)
    log.info("Iniciando reclassificação de artigos com DeepSeek...")
    log.info("=" * 60)
    
    await init_db()
    
    ai_manager = get_ai_manager()
    # Force setup
    ai_manager._setup_providers()
    
    if not ai_manager.providers:
        log.error("Nenhum provedor de IA configurado. Abortando.")
        return

    async with get_session_context() as db:
        # Garantir que categorias novas existam
        from app.models import DEFAULT_CATEGORIES
        
        # Carregar categorias existentes
        result = await db.execute(select(Category))
        existing_cats = {c.slug: c for c in result.scalars().all()}
        
        # Inserir ou atualizar defaults
        for cat_data in DEFAULT_CATEGORIES:
            slug = cat_data["slug"]
            if slug not in existing_cats:
                log.info(f"Criando nova categoria: {cat_data['name']}")
                new_cat = Category(**cat_data)
                db.add(new_cat)
            else:
                # Opcional: atualizar keywords se mudaram
                cat = existing_cats[slug]
                if cat.keywords != cat_data["keywords"]:
                    cat.keywords = cat_data["keywords"]
                    log.info(f"Atualizando keywords da categoria: {cat.name}")
        
        await db.commit()

        # Recarregar mapeamento slug -> id
        result = await db.execute(select(Category))
        categories = {c.slug: c.id for c in result.scalars().all()}
        
        # Buscar artigos
        # Podemos filtrar apenas aqueles com confiança baixa ou todos?
        # O usuário pediu "tudo", então vamos pegar todos.
        result = await db.execute(select(Article))
        articles = result.scalars().all()
        
        log.info(f"Total de artigos para processar: {len(articles)}")
        
        processed = 0
        updated = 0
        errors = 0
        
        for article in articles:
            processed += 1
            print(f"[{processed}/{len(articles)}] Processando: {article.title[:50]}...", end="\r")
            
            try:
                # Montar texto
                text_parts = [article.title]
                if article.abstract:
                    text_parts.append(article.abstract)
                if article.keywords:
                    text_parts.append(article.keywords)
                
                text = " ".join(text_parts)
                
                # Classificar
                category_slug, confidence, provider = await ai_manager.classify(text)
                
                if category_slug and category_slug != "outros":
                    cat_id = categories.get(category_slug)
                    
                    if cat_id:
                        # Só atualizar se mudou algo ou se a confiança melhorou significativamente
                        if article.category_id != cat_id or (article.classification_confidence or 0) < confidence:
                            stmt = update(Article).where(Article.id == article.id).values(
                                category_id=cat_id,
                                classification_confidence=confidence
                            )
                            await db.execute(stmt)
                            updated += 1
                            log.info(f"  -> Atualizado: {article.title[:30]}... | {category_slug} ({confidence}) via {provider}")
                    else:
                        log.warning(f"  -> Categoria retornada '{category_slug}' não encontrada no banco.")
                
            except Exception as e:
                log.error(f"Erro ao processar artigo {article.id}: {e}")
                errors += 1
                
            # Commit a cada X artigos para não segurar transação
            if processed % 10 == 0:
                await db.commit()
                
            # Pequeno delay para rate limits
            await asyncio.sleep(0.5)

        await db.commit()
        
        log.info("")
        log.info("=" * 60)
        log.info("RESUMO DA RECLASSIFICAÇÃO")
        log.info(f"  Processados: {processed}")
        log.info(f"  Atualizados: {updated}")
        log.info(f"  Erros: {errors}")
        log.info("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(reprocess_classification())
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
    except Exception as e:
        log.error(f"Erro fatal: {e}")
