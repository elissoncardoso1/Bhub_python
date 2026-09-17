# ruff: noqa: ARG001, ARG002, B017
"""Testes unitários do task_dispatcher: abstração ITaskQueue e sem fallback silencioso.

RED→GREEN para o épico 1 (T1.1 + T1.2) do plano BHub v1.1:
- ArqTaskQueue enfileira com nomes de job exatos e _defer_by na classificação.
- Redis indisponível com enable_arq=True levanta erro explícito (nunca create_task).
- InlineTaskQueue (apenas dev/test) executa inline, sem create_task solto.
- Fachada dispatch_* mantém assinaturas para os call sites existentes.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import app.services.task_dispatcher as dispatcher
from app.config import settings
from app.services.task_dispatcher import (
    dispatch_classify_article,
    dispatch_download_pdf,
)


@pytest.fixture
def arq_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_arq", True)


@pytest.fixture
def arq_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_arq", False)


@pytest.fixture(autouse=True)
def reset_dispatcher_state(monkeypatch: pytest.MonkeyPatch):
    """Isola o pool ARQ e a fila entre os testes."""
    monkeypatch.setattr(dispatcher, "_arq_pool", None)
    yield
    # não deixa tasks pendentes do InlineTaskQueue sobreviverem ao teste
    for t in list(getattr(dispatcher, "_pending_inline_tasks", []) or []):
        t.cancel()


class FakeJob:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


class FakeArqPool:
    """Pool ARQ falso para inspecionar as chamadas de enqueue_job."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> FakeJob:
        self.calls.append({"function": function, "args": args, "kwargs": kwargs})
        return FakeJob(f"arq-job-{len(self.calls)}")


class BrokenArqPool:
    """Pool que simula Redis indisponível."""

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> FakeJob:
        raise ConnectionError("redis indisponível")


# ---------------------------------------------------------------------------
# ArqTaskQueue
# ---------------------------------------------------------------------------


async def test_arq_queue_dispatch_classification_com_defer_by():
    from app.interfaces.task_queue import ArqTaskQueue

    pool = FakeArqPool()
    queue = ArqTaskQueue(pool_factory=lambda: pool)

    job_id = await queue.dispatch_classification(article_id=42)

    assert job_id.startswith("arq-job-")
    assert pool.calls == [
        {
            "function": "task_classify_article",
            "args": (42,),
            "kwargs": {"_defer_by": 2},
        }
    ]


async def test_arq_queue_dispatch_pdf_sem_defer_by():
    from app.interfaces.task_queue import ArqTaskQueue

    pool = FakeArqPool()
    queue = ArqTaskQueue(pool_factory=lambda: pool)

    job_id = await queue.dispatch_pdf(article_id=7, pdf_url="https://x/paper.pdf")

    assert job_id.startswith("arq-job-")
    assert pool.calls == [
        {
            "function": "task_download_pdf",
            "args": (7, "https://x/paper.pdf"),
            "kwargs": {},
        }
    ]


async def test_arq_queue_redis_indisponivel_levanta_erro_explicito():
    """T1.2: com ARQ habilitado, falha de Redis é erro — nunca fallback local."""
    from app.interfaces.task_queue import ArqTaskQueue

    queue = ArqTaskQueue(pool_factory=lambda: BrokenArqPool())

    with pytest.raises(Exception) as excinfo:
        await queue.dispatch_classification(article_id=1)
    assert "redis indisponível" in str(excinfo.value)

    with pytest.raises(Exception):
        await queue.dispatch_pdf(article_id=1, pdf_url=None)


# ---------------------------------------------------------------------------
# InlineTaskQueue (dev/test apenas)
# ---------------------------------------------------------------------------


async def test_inline_queue_executa_classificacao_inline(monkeypatch):
    from app.interfaces.task_queue import InlineTaskQueue

    executed: list[int] = []

    async def fake_classify(article_id: int) -> None:
        executed.append(article_id)

    import app.services.background_tasks as bt

    monkeypatch.setattr(bt, "classify_article_task", fake_classify)

    queue = InlineTaskQueue()
    job_id = await queue.dispatch_classification(article_id=99)
    await queue.wait_pending()

    assert 99 in executed
    assert job_id == "inline-classify-99"


async def test_inline_queue_executa_pdf_inline(monkeypatch):
    from app.interfaces.task_queue import InlineTaskQueue

    executed: list[tuple[int, str | None]] = []

    async def fake_process(self, article_id, pdf_url=None, db=None):
        executed.append((article_id, pdf_url))

    monkeypatch.setattr("app.services.pdf_service.PDFService.process_article_pdf", fake_process)

    queue = InlineTaskQueue()
    job_id = await queue.dispatch_pdf(article_id=5, pdf_url="https://x/y.pdf")
    await queue.wait_pending()

    # T1.3: o executor inline honra o pdf_url do contrato, usando a mesma
    # operação transacional do job ARQ.
    assert executed == [(5, "https://x/y.pdf")]
    assert job_id == "inline-pdf-5"


async def test_inline_queue_gerencia_suas_tasks_sem_soltar_create_task(monkeypatch):
    """InlineTaskQueue usa executor local explícito e aguarda/gerencia as tasks."""
    import app.interfaces.task_queue as tq

    started = asyncio.Event()
    finished = False

    async def slow_classify(article_id: int) -> None:
        nonlocal finished
        started.set()
        await asyncio.sleep(0.05)
        finished = True

    import app.services.background_tasks as bt

    monkeypatch.setattr(bt, "classify_article_task", slow_classify)

    queue = tq.InlineTaskQueue()
    await queue.dispatch_classification(article_id=1)
    await started.wait()
    # o InlineTaskQueue controla o ciclo de vida das tasks que cria
    await queue.wait_pending()
    assert finished


async def test_inline_queue_erro_no_job_nao_propaga_nem_quebra_fila(monkeypatch):
    """Erros no trabalho inline são registrados, não sobem para o caller."""
    import app.interfaces.task_queue as tq

    async def boom(article_id: int) -> None:
        raise RuntimeError("falhou no processamento")

    import app.services.background_tasks as bt

    monkeypatch.setattr(bt, "classify_article_task", boom)

    queue = tq.InlineTaskQueue()
    job_id = await queue.dispatch_classification(article_id=1)
    assert job_id == "inline-classify-1"
    await queue.wait_pending()  # não deve lançar


# ---------------------------------------------------------------------------
# Fachada dispatch_* (contrato público mantido)
# ---------------------------------------------------------------------------


async def test_dispatch_classify_usa_arq_quando_habilitado(arq_enabled, monkeypatch):
    from app.interfaces.task_queue import ArqTaskQueue

    pool = FakeArqPool()
    monkeypatch.setattr(
        dispatcher,
        "get_task_queue",
        lambda: ArqTaskQueue(pool_factory=lambda: pool),
    )

    job_id = await dispatch_classify_article(42)

    assert pool.calls[0]["function"] == "task_classify_article"
    assert pool.calls[0]["args"] == (42,)
    assert job_id.startswith("arq-job-")


async def test_dispatch_pdf_usa_arq_quando_habilitado(arq_enabled, monkeypatch):
    from app.interfaces.task_queue import ArqTaskQueue

    pool = FakeArqPool()
    monkeypatch.setattr(
        dispatcher,
        "get_task_queue",
        lambda: ArqTaskQueue(pool_factory=lambda: pool),
    )

    job_id = await dispatch_download_pdf(10, "https://x/a.pdf")

    assert pool.calls[0]["function"] == "task_download_pdf"
    assert job_id.startswith("arq-job-")


async def test_dispatch_com_arq_habilitado_e_redis_fora_erro_explicito(
    arq_enabled, monkeypatch, caplog
):
    """T1.2: produção (enable_arq=True) falha explícito — sem asyncio.create_task."""
    from app.interfaces.task_queue import ArqTaskQueue

    original_create_task = asyncio.create_task
    calls_to_create_task: list[Any] = []

    def spy_create_task(*args: Any, **kwargs: Any):  # noqa: ARG001
        calls_to_create_task.append(args)
        return original_create_task(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_task", spy_create_task)
    monkeypatch.setattr(
        dispatcher,
        "get_task_queue",
        lambda: ArqTaskQueue(pool_factory=lambda: BrokenArqPool()),
    )

    with pytest.raises(Exception):
        await dispatch_classify_article(1)

    with pytest.raises(Exception):
        await dispatch_download_pdf(1, None)

    assert calls_to_create_task == []


async def test_dispatch_sem_arq_usa_inline(arq_disabled, monkeypatch):
    executed: list[int] = []

    async def fake_classify(article_id: int) -> None:
        executed.append(article_id)

    import app.services.background_tasks as bt

    monkeypatch.setattr(bt, "classify_article_task", fake_classify)

    job_id = await dispatch_classify_article(7)
    await dispatcher.close_task_queue()

    assert 7 in executed
    assert job_id == "inline-classify-7"


async def test_dispatch_pdf_sem_arq_usa_inline(arq_disabled, monkeypatch):
    executed: list[tuple[int, str | None]] = []

    async def fake_process(self, article_id, pdf_url=None, db=None):
        executed.append((article_id, pdf_url))

    monkeypatch.setattr("app.services.pdf_service.PDFService.process_article_pdf", fake_process)

    job_id = await dispatch_download_pdf(3, "https://x/z.pdf")
    await dispatcher.close_task_queue()

    assert executed == [(3, "https://x/z.pdf")]  # T1.3: pdf_url honrado no inline
    assert job_id == "inline-pdf-3"


async def test_inline_queue_permitido_apenas_sem_arq(arq_disabled):
    """get_task_queue retorna InlineTaskQueue apenas quando ARQ está desativado."""
    from app.interfaces.task_queue import InlineTaskQueue

    queue = dispatcher.get_task_queue()
    assert isinstance(queue, InlineTaskQueue)


async def test_get_task_queue_retorna_arq_quando_habilitado(arq_enabled):
    from app.interfaces.task_queue import ArqTaskQueue

    assert isinstance(dispatcher.get_task_queue(), ArqTaskQueue)


async def test_dispatch_com_arq_e_pool_nao_inicializado_erro_explicito(arq_enabled):
    """Com ARQ habilitado mas pool não inicializado, o erro é explícito."""
    with pytest.raises(RuntimeError, match="ARQ pool não inicializado"):
        await dispatch_classify_article(1)


async def test_log_estruturado_em_falha_de_enfileiramento(arq_enabled, monkeypatch):
    """Falha de enfileiramento em produção gera log estruturado (ERROR) antes de propagar."""
    from loguru import logger as loguru_logger

    from app.interfaces.task_queue import ArqTaskQueue

    captured: list[dict[str, Any]] = []

    def sink(message) -> None:
        captured.append({"level": message.record["level"].name, "text": str(message)})

    handler_id = loguru_logger.add(sink, level="DEBUG")
    try:
        monkeypatch.setattr(
            dispatcher,
            "get_task_queue",
            lambda: ArqTaskQueue(pool_factory=lambda: BrokenArqPool()),
        )

        with pytest.raises(Exception):
            await dispatch_classify_article(1)
    finally:
        loguru_logger.remove(handler_id)

    record = next(
        (r for r in captured if "arq_enqueue_failed" in r["text"]),
        None,
    )
    assert record is not None, "esperado log de ERROR estruturado ao falhar enqueue"
    assert record["level"] == "ERROR"
