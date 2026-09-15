"""Estratégias explícitas de execução de jobs (fila de tarefas).

Contrato mínimo (T1.1 do plano BHub v1.1):

- ``ArqTaskQueue``: enfileira jobs persistentes no Redis via ARQ. É a única
  estratégia permitida em produção (``ENABLE_ARQ=true``). Falhas de conexão
  são propagadas como erro explícito — nunca há degradação silenciosa.
- ``InlineTaskQueue``: executor local explícito, permitido APENAS em
  desenvolvimento/testes (``ENABLE_ARQ=false``). Executa o trabalho no
  event loop atual com tarefas rastreadas (ver ``wait_pending``).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Protocol

from app.core.logging import log

CLASSIFY_JOB_NAME = "task_classify_article"
DOWNLOAD_PDF_JOB_NAME = "task_download_pdf"
CLASSIFY_DEFER_BY_SECONDS = 2

PoolFactory = Callable[[], Any]


class ITaskQueue(Protocol):
    """Contrato estrutural de uma fila de tarefas do BHub."""

    async def dispatch_classification(self, article_id: int) -> str:
        """Enfileira classificação do artigo e retorna o job_id."""
        ...

    async def dispatch_pdf(self, article_id: int, pdf_url: str | None) -> str:
        """Enfileira download de PDF e retorna o job_id."""
        ...


class ArqTaskQueue:
    """Fila persistente via ARQ/Redis — obrigatória em produção."""

    def __init__(self, pool_factory: PoolFactory) -> None:
        self._pool_factory = pool_factory

    async def _enqueue(self, function: str, *args: Any, **kwargs: Any) -> str:
        try:
            pool = self._pool_factory()
            job = await pool.enqueue_job(function, *args, **kwargs)
            return job.job_id
        except Exception as e:
            # T1.2: falha de enfileiramento com ARQ habilitado é erro
            # explícito com log estruturado — sem fallback silencioso.
            log.error(
                "falha_enfileirar_arq | "
                f"event=arq_enqueue_failed function={function} "
                f"args={args!r} error_type={type(e).__name__} error={e}"
            )
            raise

    async def dispatch_classification(self, article_id: int) -> str:
        return await self._enqueue(
            CLASSIFY_JOB_NAME,
            article_id,
            _defer_by=CLASSIFY_DEFER_BY_SECONDS,
        )

    async def dispatch_pdf(self, article_id: int, pdf_url: str | None) -> str:
        return await self._enqueue(DOWNLOAD_PDF_JOB_NAME, article_id, pdf_url)


class InlineTaskQueue:
    """Executor local explícito — uso exclusivo de dev/test (ENABLE_ARQ=false).

    O trabalho roda no event loop atual como ``asyncio.Task`` criada e
    rastreada aqui (``_pending``). Este é o ÚNICO ponto do código em que
    ``asyncio.create_task`` é permitido, e apenas quando ARQ está
    desativado — em produção (``ENABLE_ARQ=true``) a fila usada é a
    ``ArqTaskQueue``, que nunca degrada para execução local.
    """

    def __init__(self) -> None:
        self._pending: set[asyncio.Task[None]] = set()

    async def _run_inline(self, coro_factory: Callable[[], Any], job_id: str) -> None:
        task = asyncio.create_task(coro_factory(), name=job_id)
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def wait_pending(self) -> None:
        """Aguarda todas as tarefas inline pendentes terminarem."""
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)

    async def dispatch_classification(self, article_id: int) -> str:
        from app.services.background_tasks import classify_article_task

        job_id = f"inline-classify-{article_id}"
        await self._run_inline(lambda: classify_article_task(article_id), job_id)
        return job_id

    async def dispatch_pdf(self, article_id: int, pdf_url: str | None) -> str:
        """Enfileira download de PDF e retorna o job_id.

        T1.3: roda a mesma operação transacional do job ARQ —
        ``PDFService.process_article_pdf`` — honrando o ``pdf_url`` do
        contrato ITaskQueue (antes o executor inline descartava o
        argumento). Erros são registrados, não propagados: no executor
        local não há retry do worker para acionar.
        """
        from app.services.pdf_service import PDFService

        job_id = f"inline-pdf-{article_id}"

        async def run_inline_pdf() -> None:
            try:
                service = PDFService()
                result = await service.process_article_pdf(article_id, pdf_url)
                if result is None:
                    log.debug(f"job inline de PDF sem trabalho (artigo {article_id})")
            except Exception as e:
                log.error(
                    f"job inline de PDF falhou (artigo {article_id}): {e}"
                )

        await self._run_inline(run_inline_pdf, job_id)
        return job_id
