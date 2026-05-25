"""Dispatcher de tarefas persistentes via ARQ, com fallback local para dev/test."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from app.config import settings
from app.core.logging import log

_arq_pool: Any | None = None


async def get_arq_pool() -> Any:
    """Retorna o pool ARQ inicializado sob demanda."""
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool

    try:
        from arq.connections import RedisSettings, create_pool
    except ImportError as exc:
        raise RuntimeError("ARQ não está instalado") from exc

    _arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _arq_pool


async def close_arq_pool() -> None:
    """Fecha o pool ARQ se ele tiver sido criado."""
    global _arq_pool
    if _arq_pool is None:
        return

    close = getattr(_arq_pool, "close", None)
    wait_closed = getattr(_arq_pool, "wait_closed", None)
    if close:
        result = close()
        if inspect.isawaitable(result):
            await result
    if wait_closed:
        await wait_closed()
    _arq_pool = None


async def dispatch_classify_article(article_id: int) -> str:
    """Enfileira classificação e retorna job_id; em dev/test, cai para task local."""
    if settings.enable_arq:
        try:
            pool = await get_arq_pool()
            job = await pool.enqueue_job(
                "task_classify_article",
                article_id,
                _defer_by=2,
            )
            return job.job_id
        except Exception as e:
            log.warning(f"Falha ao enfileirar classificação no ARQ; usando fallback local: {e}")

    from app.services.background_tasks import classify_article_task

    asyncio.create_task(classify_article_task(article_id))
    return f"local-classify-{article_id}"


async def dispatch_download_pdf(article_id: int, pdf_url: str | None = None) -> str:
    """Enfileira download de PDF e retorna job_id; em dev/test, cai para task local."""
    if settings.enable_arq:
        try:
            pool = await get_arq_pool()
            job = await pool.enqueue_job("task_download_pdf", article_id, pdf_url)
            return job.job_id
        except Exception as e:
            log.warning(f"Falha ao enfileirar download no ARQ; usando fallback local: {e}")

    from app.services.background_tasks import download_pdf_task

    asyncio.create_task(download_pdf_task(article_id))
    return f"local-pdf-{article_id}"
