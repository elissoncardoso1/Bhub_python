"""Tarefas ARQ para processamento assíncrono persistente."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

try:
    from arq.connections import RedisSettings

    from app.config import settings

    _redis_settings = RedisSettings.from_dsn(settings.redis_url)
except ImportError:
    _redis_settings = None


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


async def task_download_pdf(
    ctx: dict[str, Any],
    article_id: int,
    pdf_url: str | None = None,
) -> dict[str, Any]:
    """Baixa PDF de artigo open access em job persistente."""
    from app.services.background_tasks import download_pdf_task

    # Mantém a lógica atual centralizada enquanto o PDFService não expõe uma
    # operação transacional única para article_id.
    await download_pdf_task(article_id)
    return {"article_id": article_id, "pdf_url": pdf_url, "status": "processed"}


async def startup(ctx: dict[str, Any]) -> None:
    from app.database import async_session_maker

    ctx["session_factory"] = async_session_maker


async def shutdown(ctx: dict[str, Any]) -> None:
    session: AsyncSession | None = ctx.pop("db", None)
    if session:
        await session.close()


async def on_job_start(ctx: dict[str, Any]) -> None:
    session_factory = ctx["session_factory"]
    ctx["db"] = session_factory()


async def on_job_end(ctx: dict[str, Any]) -> None:
    session: AsyncSession | None = ctx.pop("db", None)
    if session:
        await session.close()


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
