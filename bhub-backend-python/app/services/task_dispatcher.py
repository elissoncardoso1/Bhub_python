"""Dispatcher de tarefas via fila explícita (ITaskQueue).

Estratégias:
- ``ENABLE_ARQ=true``  → ``ArqTaskQueue`` (Redis/ARQ). Falha de enfileiramento
  é erro explícito — NUNCA degrada para execução local (T1.2).
- ``ENABLE_ARQ=false`` → ``InlineTaskQueue``, executor local explícito
  permitido apenas em dev/test.

As funções ``dispatch_*`` são fachadas que preservam as assinaturas públicas
usadas por ``app/services/feed_aggregator.py`` e ``app/api/``.
"""

from __future__ import annotations

import inspect
from typing import Any

from app.config import settings
from app.core.logging import log
from app.interfaces.task_queue import ArqTaskQueue, InlineTaskQueue

_arq_pool: Any | None = None
_inline_queue: InlineTaskQueue | None = None


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


async def close_task_queue() -> None:
    """Fecha os recursos da fila ativa (pool ARQ e tarefas inline pendentes)."""
    global _inline_queue
    if _inline_queue is not None:
        await _inline_queue.wait_pending()
        _inline_queue = None
    await close_arq_pool()


def get_task_queue() -> ArqTaskQueue | InlineTaskQueue:
    """Retorna a fila de tarefas conforme a configuração.

    - ARQ habilitado → ArqTaskQueue (produção). Erros de conexão propagam.
    - ARQ desativado → InlineTaskQueue (apenas dev/test).
    """
    if settings.enable_arq:
        return ArqTaskQueue(pool_factory=lambda: _require_arq_pool())

    global _inline_queue
    if _inline_queue is None:
        _inline_queue = InlineTaskQueue()
    return _inline_queue


def _require_arq_pool() -> Any:
    """Expõe o pool ARQ já inicializado; propaga erros de forma explícita."""
    if _arq_pool is None:
        raise RuntimeError(
            "ARQ pool não inicializado — chame get_arq_pool() no startup. "
            "Recusa explícita: execução local não é permitida com ENABLE_ARQ=true."
        )
    return _arq_pool


async def dispatch_classify_article(article_id: int) -> str:
    """Enfileira classificação via fila explícita e retorna job_id."""
    queue = get_task_queue()
    try:
        return await queue.dispatch_classification(article_id)
    except Exception:
        raise


async def dispatch_download_pdf(article_id: int, pdf_url: str | None = None) -> str:
    """Enfileira download de PDF via fila explícita e retorna job_id."""
    queue = get_task_queue()
    log.debug(f"Dispatch PDF via {type(queue).__name__} artigo={article_id}")
    return await queue.dispatch_pdf(article_id, pdf_url)
