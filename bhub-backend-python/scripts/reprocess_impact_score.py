"""
Script para reprocessar impact_score de artigos existentes.
Atualiza artigos que ainda têm o valor padrão (5.0) ou None.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.core.logging import setup_logging, log
from app.database import get_session_context, init_db
from app.models import Article
from app.ml.impact_rating import ImpactRatingService
from sqlalchemy import select, update

async def reprocess_impact_scores():
    """Reprocessa impact_score para artigos que ainda têm valor padrão."""
    setup_logging()
    log.info("=" * 60)
    log.info("REPROCESSAMENTO DE IMPACT SCORE")
    log.info("=" * 60)
    
    # Inicializar banco de dados
    await init_db()
    
    async with get_session_context() as db:
        # Buscar artigos com impact_score padrão ou None
        # Usar comparação com tolerância para float
        from sqlalchemy import or_
        stmt = select(Article).where(
            or_(
                Article.impact_score.is_(None),
                Article.impact_score == 5.0
            )
        )
        result = await db.execute(stmt)
        articles = result.scalars().all()
        
        total = len(articles)
        log.info(f"Encontrados {total} artigos para reprocessar")
        
        if total == 0:
            log.info("Nenhum artigo precisa ser reprocessado!")
            return
        
        processed = 0
        updated = 0
        errors = 0
        
        for article in articles:
            processed += 1
            print(f"[{processed}/{total}] Processando: {article.title[:50]}...", end="\r")
            
            try:
                # Calcular impact_score
                impact_score = await ImpactRatingService.calculate_impact(
                    title=article.title,
                    abstract=article.abstract,
                    keywords=article.keywords,
                    journal_name=article.journal_name,
                    has_doi=bool(article.doi),
                )
                
                # Atualizar apenas se o score mudou significativamente (tolerância para float)
                current_score = article.impact_score or 5.0
                if abs(current_score - impact_score) > 0.01:
                    article.impact_score = impact_score
                    updated += 1
                    log.info(f"  -> Atualizado: {article.title[:30]}... | Score: {current_score:.2f} -> {impact_score:.2f}")
                
            except Exception as e:
                log.error(f"Erro ao processar artigo {article.id}: {e}")
                errors += 1
            
            # Commit a cada 10 artigos
            if processed % 10 == 0:
                await db.commit()
        
        # Commit final
        await db.commit()
        
        log.info("=" * 60)
        log.info(f"Processamento concluído!")
        log.info(f"  Total processado: {processed}")
        log.info(f"  Atualizados: {updated}")
        log.info(f"  Erros: {errors}")
        log.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(reprocess_impact_scores())

