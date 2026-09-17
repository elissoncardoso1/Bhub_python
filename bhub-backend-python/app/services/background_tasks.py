"""
Serviço de tarefas em segundo plano.
"""

from sqlalchemy import select

from app.core.logging import log
from app.database import get_session_context
from app.models import Article


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
            from app.ai import get_ai_manager
            from app.ml import ImpactRatingService
            from app.services.classification_service import ClassificationService

            ai_manager = get_ai_manager()

            # Usar novo serviço de classificação com suporte a múltiplas categorias
            category_slugs_with_confidence = (
                await ClassificationService.classify_with_multiple_categories(
                    db=db,
                    text=classification_text,
                    ai_manager=ai_manager,
                    min_confidence=0.3,
                )
            )

            # Calcular impact_score se ainda não foi calculado (ou se está no valor padrão)
            needs_impact_calculation = (
                article.impact_score is None
                or abs(article.impact_score - 5.0) < 0.01  # Tolerância para comparação de float
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

            # Atribuir múltiplas categorias ao artigo
            if category_slugs_with_confidence:
                assigned_categories = await ClassificationService.assign_categories_to_article(
                    db=db,
                    article_id=article_id,
                    category_slugs_with_confidence=category_slugs_with_confidence,
                    auto_create=True,  # Criar categorias automaticamente se necessário
                )

                # Atualizar confiança média (ou da primeira categoria)
                if assigned_categories:
                    primary_confidence = (
                        category_slugs_with_confidence[0][1]
                        if category_slugs_with_confidence
                        else 0.0
                    )
                    article.classification_confidence = primary_confidence

                    await db.commit()
                    category_names = ", ".join([cat.name for cat in assigned_categories])
                    log.info(
                        f"Artigo {article_id} atualizado com {len(assigned_categories)} categorias: {category_names}, impact_score: {article.impact_score:.2f}"
                    )
                else:
                    log.warning(f"Nenhuma categoria atribuída ao artigo {article_id}")
            else:
                # Mesmo sem categoria, salvar o impact_score se foi calculado
                if abs(article.impact_score - 5.0) >= 0.01:
                    await db.commit()
                    log.info(
                        f"Artigo {article_id} - Impact score atualizado: {article.impact_score:.2f} (sem categoria)"
                    )
                else:
                    log.info(f"Nenhuma categoria determinada para artigo {article_id}")

    except Exception as e:
        log.error(f"Erro fatal na task de classificação (Artigo {article_id}): {e}")
