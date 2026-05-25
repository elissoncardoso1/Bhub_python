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
            category_slugs_with_confidence = await ClassificationService.classify_with_multiple_categories(
                db=db,
                text=classification_text,
                ai_manager=ai_manager,
                min_confidence=0.3,
            )

            # Calcular impact_score se ainda não foi calculado (ou se está no valor padrão)
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
                    primary_confidence = category_slugs_with_confidence[0][1] if category_slugs_with_confidence else 0.0
                    article.classification_confidence = primary_confidence

                    await db.commit()
                    category_names = ", ".join([cat.name for cat in assigned_categories])
                    log.info(f"Artigo {article_id} atualizado com {len(assigned_categories)} categorias: {category_names}, impact_score: {article.impact_score:.2f}")
                else:
                    log.warning(f"Nenhuma categoria atribuída ao artigo {article_id}")
            else:
                # Mesmo sem categoria, salvar o impact_score se foi calculado
                if abs(article.impact_score - 5.0) >= 0.01:
                    await db.commit()
                    log.info(f"Artigo {article_id} - Impact score atualizado: {article.impact_score:.2f} (sem categoria)")
                else:
                    log.info(f"Nenhuma categoria determinada para artigo {article_id}")

    except Exception as e:
        log.error(f"Erro fatal na task de classificação (Artigo {article_id}): {e}")


async def download_pdf_task(article_id: int):
    """
    Tarefa em segundo plano para baixar PDF de um artigo open access.
    """
    log.info(f"Iniciando download de PDF em background para artigo ID: {article_id}")

    try:
        async with get_session_context() as db:
            # Buscar artigo
            result = await db.execute(select(Article).where(Article.id == article_id))
            article = result.scalar_one_or_none()

            if not article:
                log.warning(f"Artigo {article_id} não encontrado para download de PDF")
                return

            # Verificar se já tem PDF
            if article.pdf_file_path:
                log.info(f"Artigo {article_id} já possui PDF: {article.pdf_file_path}")
                return

            # Verificar se é open access
            if not article.is_open_access:
                log.debug(f"Artigo {article_id} não é open access, pulando download")
                return

            # Tentar obter URL do PDF
            pdf_url = article.pdf_url
            if not pdf_url:
                # Tentar construir URL do PDF a partir da URL do artigo
                if article.original_url:
                    # Padrões comuns para URLs de PDF
                    potential_urls = [
                        article.original_url.replace("/article/", "/pdf/"),
                        article.original_url.replace("/article/", "/download/"),
                        article.original_url + ".pdf",
                        article.original_url + "/pdf",
                    ]

                    # Tentar cada URL potencial
                    from app.services.pdf_service import PDFService
                    pdf_service = PDFService()

                    for url in potential_urls:
                        log.info(f"Tentando baixar PDF de: {url}")
                        pdf_data = await pdf_service.download_pdf_from_url(
                            url,
                            article.title,
                            db,
                        )
                        if pdf_data:
                            pdf_url = url
                            break
                else:
                    log.warning(f"Artigo {article_id} não tem URL do artigo nem PDF URL")
                    return
            else:
                # Usar URL do PDF diretamente
                from app.services.pdf_service import PDFService
                pdf_service = PDFService()
                pdf_data = await pdf_service.download_pdf_from_url(
                    pdf_url,
                    article.title,
                    db,
                )

            if not pdf_data:
                log.warning(f"Não foi possível baixar PDF para artigo {article_id}")
                return

            # Verificar duplicata novamente (pode ter sido adicionado por outra task)
            if await pdf_service.check_duplicate(pdf_data["file_hash"], db):
                log.info(f"PDF duplicado detectado para artigo {article_id}, removendo arquivo")
                from pathlib import Path
                Path(pdf_data["file_path"]).unlink(missing_ok=True)
                return

            # Atualizar artigo com dados do PDF
            article.pdf_file_path = pdf_data["file_path"]
            article.pdf_file_size = pdf_data["file_size"]

            # Criar ou atualizar metadados do PDF
            from sqlalchemy import select as sql_select

            from app.models import PDFMetadata, ProcessingStatus

            pdf_meta_result = await db.execute(
                sql_select(PDFMetadata).where(PDFMetadata.article_id == article_id)
            )
            pdf_metadata = pdf_meta_result.scalar_one_or_none()

            if pdf_metadata:
                # Atualizar existente
                pdf_metadata.file_hash = pdf_data["file_hash"]
                pdf_metadata.original_filename = pdf_data["original_filename"]
                pdf_metadata.page_count = pdf_data.get("page_count")
                pdf_metadata.word_count = pdf_data.get("word_count")
                pdf_metadata.extracted_text = pdf_data.get("extracted_text")
                pdf_metadata.pdf_info = str(pdf_data.get("pdf_info", {}))
                pdf_metadata.processing_status = ProcessingStatus.COMPLETED
                pdf_metadata.processing_error = None
            else:
                # Criar novo
                pdf_metadata = PDFMetadata(
                    article_id=article_id,
                    file_hash=pdf_data["file_hash"],
                    original_filename=pdf_data["original_filename"],
                    page_count=pdf_data.get("page_count"),
                    word_count=pdf_data.get("word_count"),
                    extracted_text=pdf_data.get("extracted_text"),
                    pdf_info=str(pdf_data.get("pdf_info", {})),
                    processing_status=ProcessingStatus.COMPLETED,
                )
                db.add(pdf_metadata)

            await db.commit()
            log.info(f"PDF baixado e associado ao artigo {article_id}: {pdf_data['file_path']}")

    except Exception as e:
        log.error(f"Erro fatal na task de download de PDF (Artigo {article_id}): {e}")
