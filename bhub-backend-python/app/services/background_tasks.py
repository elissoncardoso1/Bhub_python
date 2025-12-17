"""
Serviço de tarefas em segundo plano.
"""

from app.core.logging import log
from app.database import get_session_context
from app.models import Article, Category
from sqlalchemy import select

async def classify_article_task(article_id: int):
    """
    Tarefa em segundo plano para classificar um artigo.
    Executa a lógica de classificação (AI/ML/Heurística) e atualiza o artigo.
    """
    log.info(f"Iniciando classificação em background para artigo ID: {article_id}")
    
    try:
        async with get_session_context() as db:
            # Buscar artigo
            result = await db.execute(select(Article).where(Article.id == article_id))
            article = result.scalar_one_or_none()
            
            if not article:
                log.warning(f"Artigo {article_id} não encontrado para classificação")
                return
                
            # Preparar texto
            text_parts = [article.title]
            if article.abstract:
                text_parts.append(article.abstract)
            if article.keywords:
                text_parts.append(article.keywords)
            
            classification_text = " ".join(text_parts)
            
            # Imports locais para evitar ciclos ou manter padrão
            from app.ml import EmbeddingClassifier, HeuristicClassifier, ImpactRatingService
            from app.ai import get_ai_manager
            
            ai_manager = get_ai_manager()
            category_slug = None
            classification_confidence = 0.0
            external_success = False
            
            # 1. Tentar IA Externa
            if any(p in ai_manager.providers for p in ["deepseek", "openrouter"]):
                try:
                    cat_slug, conf, provider = await ai_manager.classify(classification_text)
                    if cat_slug != "outros" or conf > 0.0:
                        category_slug = cat_slug
                        classification_confidence = conf
                        external_success = True
                        log.debug(f"Artigo {article_id} classificado via {provider}: {category_slug} (conf: {conf:.2f})")
                except Exception as e:
                    log.warning(f"Falha na classificação externa (Artigo {article_id}): {e}")
            
            # 2. Fallback para ML Local
            if not external_success and EmbeddingClassifier.is_initialized():
                try:
                    category_slug, confidence = await EmbeddingClassifier.classify(classification_text)
                    if not category_slug and not external_success: 
                        # Se ML local retornou None ou falhou silenciosamente (improvável, mas ok)
                        pass
                    else:
                        classification_confidence = confidence
                        log.debug(f"Artigo {article_id} classificado (ML Local): {category_slug} (conf: {confidence:.2f})")
                except Exception as e:
                     log.warning(f"Erro no ML Local (Artigo {article_id}): {e}")

            # 3. Fallback para Heurística
            if not category_slug and not external_success:
                category_slug, confidence = HeuristicClassifier.classify(classification_text)
                classification_confidence = confidence
                log.debug(f"Artigo {article_id} classificado (Heurística): {category_slug} (conf: {confidence:.2f})")
            
            # Calcular impact_score se ainda não foi calculado (ou se está no valor padrão)
            # Verificar se está no valor padrão (5.0) com tolerância para comparação de float
            needs_impact_calculation = (
                article.impact_score is None or 
                abs(article.impact_score - 5.0) < 0.01  # Tolerância para comparação de float
            )
            
            if needs_impact_calculation:
                try:
                    impact_score = await ImpactRatingService.calculate_impact(
                        title=article.title,
                        abstract=article.abstract,
                        keywords=article.keywords,
                        journal_name=article.journal_name,
                        has_doi=bool(article.doi),
                    )
                    article.impact_score = impact_score
                    log.info(f"Artigo {article_id} - Impact score calculado: {impact_score:.2f}")
                except Exception as e:
                    log.warning(f"Erro ao calcular impact score (Artigo {article_id}): {e}")
            
            # Atualizar categoria no banco
            if category_slug:
                cat_result = await db.execute(select(Category).where(Category.slug == category_slug))
                category = cat_result.scalar_one_or_none()
                
                if category:
                    article.category_id = category.id
                    article.classification_confidence = classification_confidence
                    await db.commit()
                    log.info(f"Artigo {article_id} atualizado com categoria: {category.name}, impact_score: {article.impact_score:.2f}")
                else:
                    log.warning(f"Categoria slug '{category_slug}' não encontrada no banco")
            else:
                # Mesmo sem categoria, salvar o impact_score se foi calculado
                if article.impact_score != 5.0:
                    await db.commit()
                    log.info(f"Artigo {article_id} - Impact score atualizado: {article.impact_score:.2f} (sem categoria)")
                else:
                    log.info(f"Nenhuma categoria determinada para artigo {article_id}")

    except Exception as e:
        log.error(f"Erro fatal na task de classificação (Artigo {article_id}): {e}")
