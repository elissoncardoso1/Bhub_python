"""Tarefas ARQ para processamento assíncrono persistente."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.observe import observed_job

logger = logging.getLogger(__name__)

try:
    from arq.connections import RedisSettings

    from app.config import settings

    _redis_settings = RedisSettings.from_dsn(settings.redis_url)
except ImportError:
    _redis_settings = None


@observed_job("task_classify_article")
async def task_classify_article(ctx: dict[str, Any], article_id: int) -> dict[str, Any]:
    """Classifica artigo em job persistente."""
    db: AsyncSession = ctx["db"]

    from app.ai import get_ai_manager
    from app.services.classification_service import ClassificationService

    service = ClassificationService(db=db, ai_manager=get_ai_manager())
    result = await service.classify_article(article_id)
    await db.commit()

    if result is None:
        return {"article_id": article_id, "status": "not_found"}

    category_slug, confidence = result
    logger.info("Artigo %d classificado: %s (%.2f)", article_id, category_slug, confidence)
    return {
        "article_id": article_id,
        "category": category_slug,
        "confidence": confidence,
    }


@observed_job("task_download_pdf")
async def task_download_pdf(
    ctx: dict[str, Any],
    article_id: int,
    pdf_url: str | None = None,
) -> dict[str, Any]:
    """Baixa PDF de artigo open access em job persistente.

    T1.3: opera via ``PDFService.process_article_pdf`` — operação
    transacional explícita em pdf_service, sem acoplamento ao módulo
    legado de tarefas em segundo plano.

    T2.2: o serviço de PDF pode vir do contexto do job
    (``ctx["pdf_service"]``) para injeção em testes/workers; sem injeção,
    usa o construtor padrão com as configurações da aplicação.
    """
    db: AsyncSession | None = ctx.get("db")
    pdf_service = ctx.get("pdf_service")

    if pdf_service is None:
        from app.services.pdf_service import PDFService

        pdf_service = PDFService()

    if db is not None:
        result = await pdf_service.process_article_pdf(article_id, pdf_url, db=db)
    else:
        result = await pdf_service.process_article_pdf(article_id, pdf_url)

    if result is None:
        return {"article_id": article_id, "pdf_url": pdf_url, "status": "skipped"}

    return {
        "article_id": article_id,
        "pdf_url": pdf_url,
        "status": "processed",
        "file_path": result.get("file_path"),
        "file_hash": result.get("file_hash"),
    }


async def startup(ctx: dict[str, Any]) -> None:
    from app.database import async_session_maker

    ctx["session_factory"] = async_session_maker

    # T1.5: telemetria do worker — mesmo provider do app web quando ativo.
    try:
        from app.config import settings

        if settings.enable_telemetry:
            from app.core.telemetry import setup_telemetry
            from app.jobs.observe import init_job_telemetry

            setup_telemetry(settings.telemetry_service_name)
            init_job_telemetry()
    except ImportError:
        logger.debug("config indisponível — telemetria do worker desativada")

    # O fallback de classificação por embeddings precisa do modelo E dos
    # embeddings das categorias carregados NESTE processo (o lifespan do
    # app web não vale para o worker). Sem isso, task_classify_article
    # degrada para heurística/"outros".
    try:
        from app.ml import EmbeddingClassifier
        from app.models import DEFAULT_CATEGORIES

        if EmbeddingClassifier is not None:
            await EmbeddingClassifier.initialize()
            await EmbeddingClassifier.load_category_embeddings(DEFAULT_CATEGORIES)
    except Exception as e:
        logger.warning("ML não inicializado no worker: %s", e)


async def shutdown(ctx: dict[str, Any]) -> None:
    session: AsyncSession | None = ctx.pop("db", None)
    if session:
        await session.close()


async def on_job_start(ctx: dict[str, Any]) -> None:
    session_factory = ctx["session_factory"]
    ctx["db"] = session_factory()
    # T1.5: contexto de observabilidade do job (job_id/attempt/start),
    # usado pelo decorator @observed_job das tasks.
    from app.jobs.observe import init_job_obs

    init_job_obs(ctx)


async def on_job_end(ctx: dict[str, Any]) -> None:
    session: AsyncSession | None = ctx.pop("db", None)
    if session:
        await session.close()

    # T1.5: registra sucesso/falha para jobs ainda não instrumentados —
    # o decorator @observed_job já registrou os demais (sem duplicar).
    from app.jobs.observe import init_job_obs, record_job_failure, record_job_success

    obs = ctx.get("_job_obs")
    if obs is None or obs.get("recorded"):
        return
    init_job_obs(ctx)
    error = obs.get("error")
    if error is not None:
        record_job_failure(ctx, error)
    else:
        record_job_success(ctx)


class WorkerSettings:
    """Configuração central do worker ARQ."""

    functions = [task_classify_article, task_download_pdf]
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end
    max_jobs = 10
    job_timeout = 300
    max_tries = 3
    retry_jobs = True
    keep_result = 86_400
    health_check_interval = 30
    redis_settings = _redis_settings
