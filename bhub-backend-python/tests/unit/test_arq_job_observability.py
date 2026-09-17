# ruff: noqa: ARG001, ARG002
"""Testes de observabilidade dos jobs ARQ (T1.5 — plano BHub v1.1).

Todo job executado pelo worker deve registrar log estruturado com:

    job_type, job_id, article_id, attempt, status, duration, exception

e, quando OpenTelemetry está ativo, métricas ``arq.job.success``,
``arq.job.failure``, ``arq.job.duration`` e um span ``arq.job`` por job.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from loguru import logger

import app.jobs.tasks as jobs_tasks
from app.config import settings
from app.jobs.observe import record_job_failure, record_job_success
from app.jobs.tasks import WorkerSettings, on_job_end, on_job_start

JOB_TYPE_PDF = "task_download_pdf"
JOB_TYPE_CLASSIFY = "task_classify_article"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class NullSession:
    """Sessão mínima com a interface usada pelos hooks (close)."""

    async def close(self) -> None:
        pass


class FakeHistogram:
    def __init__(self) -> None:
        self.records: list[tuple[float, dict[str, Any]]] = []

    def record(self, value: float, attributes: dict[str, Any]) -> None:
        self.records.append((value, attributes))


class FakeCounter:
    def __init__(self) -> None:
        self.adds: list[tuple[int, dict[str, Any]]] = []

    def add(self, value: int, attributes: dict[str, Any]) -> None:
        self.adds.append((value, attributes))


class FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.status_calls: list[Any] = []
        self.recorded_exception: BaseException | None = None
        self.ended = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        self.status_calls.append((args, kwargs))

    def record_exception(self, exception: BaseException) -> None:
        self.recorded_exception = exception

    def end(self) -> None:
        self.ended = True


class FakeTracer:
    """Tracer falso que reproduz o comportamento do context manager real."""

    def __init__(self) -> None:
        self.span = FakeSpan()
        self.started: list[str] = []

    def start_as_current_span(self, name: str, **kwargs: Any):  # noqa: ARG002
        self.started.append(name)

        class _Ctx:
            def __enter__(_self):
                return self.span

            def __exit__(_self, *exc):
                # como o context manager real do OTel, encerra o span ao sair
                self.span.end()
                return False

        return _Ctx()


def make_ctx(job_id: str = "job-abc123", job_try: int = 1) -> dict[str, Any]:
    """ctx no formato que o worker ARQ 0.28 entrega aos hooks."""
    return {
        "job_id": job_id,
        "job_try": job_try,
        "session_factory": lambda: NullSession(),
    }


@pytest.fixture
def log_records() -> Any:
    """Captura os records do loguru emitidos durante o teste."""
    records: list[Any] = []
    handler_id = logger.add(
        lambda msg: records.append(msg.record),
        level="DEBUG",
        enqueue=False,
    )
    yield records
    logger.remove(handler_id)


def finished_logs(records: list[Any], **filters: Any) -> list[Any]:
    """Logs arq_job_finished casando com os filtros de extra."""
    return [
        r
        for r in records
        if r["message"] == "arq_job_finished"
        and all(r["extra"].get(k) == v for k, v in filters.items())
    ]


def enrich_obs(ctx: dict[str, Any], job_type: str, article_id: int | None) -> None:
    """Simula o que o decorator @observed_job faz com o ctx antes de registrar."""
    ctx["_job_obs"]["job_type"] = job_type
    ctx["_job_obs"]["article_id"] = article_id


# ---------------------------------------------------------------------------
# on_job_start: inicializa ctx de observabilidade
# ---------------------------------------------------------------------------


async def test_on_job_start_registra_ctx_de_observabilidade():
    """T1.5: on_job_start popula ctx['_job_obs'] com job_id/attempt/start
    e mantém a criação da sessão de banco (T1.4 não regride)."""
    ctx = make_ctx(job_try=2)

    await on_job_start(ctx)

    obs = ctx["_job_obs"]
    assert obs["job_id"] == "job-abc123"
    assert obs["attempt"] == 2
    assert "start" in obs
    assert obs["recorded"] is False
    # sessão de banco continua criada pelo hook
    assert ctx["db"] is not None


async def test_on_job_start_lida_com_ctx_sem_campos_arq():
    """ctx mínimo (sem job_id/job_try) não explode: attempt padrão 1."""
    ctx = {"session_factory": lambda: NullSession()}

    await on_job_start(ctx)

    assert ctx["_job_obs"]["job_id"] is None
    assert ctx["_job_obs"]["attempt"] == 1
    assert ctx["db"] is not None


# ---------------------------------------------------------------------------
# record_job_success / record_job_failure: log estruturado + métricas
# ---------------------------------------------------------------------------


async def test_record_job_success_log_com_todos_os_campos(log_records):
    ctx = make_ctx()
    await on_job_start(ctx)
    enrich_obs(ctx, JOB_TYPE_PDF, article_id=42)

    record_job_success(ctx)

    logs = finished_logs(log_records, job_id="job-abc123")
    assert logs, "nenhum log estruturado de conclusão emitido"
    extra = logs[-1]["extra"]
    assert extra["job_type"] == JOB_TYPE_PDF
    assert extra["job_id"] == "job-abc123"
    assert extra["article_id"] == 42
    assert extra["attempt"] == 1
    assert extra["status"] == "success"
    assert isinstance(extra["duration"], float)
    assert extra["duration"] >= 0
    assert "exception" not in extra


async def test_record_job_success_metricas_otel_quando_ativas(monkeypatch):
    import app.jobs.observe as observe

    success = FakeCounter()
    duration = FakeHistogram()
    monkeypatch.setattr(observe, "_job_success_counter", success)
    monkeypatch.setattr(observe, "_job_duration_histogram", duration)

    ctx = make_ctx()
    await on_job_start(ctx)
    enrich_obs(ctx, JOB_TYPE_PDF, article_id=42)
    time.sleep(0.01)
    record_job_success(ctx)

    assert success.adds == [(1, {"job_type": JOB_TYPE_PDF})]
    assert len(duration.records) == 1
    recorded_duration, attrs = duration.records[0]
    assert attrs == {"job_type": JOB_TYPE_PDF}
    assert recorded_duration > 0


async def test_record_job_failure_log_com_exception(log_records):
    ctx = make_ctx(job_try=2)
    await on_job_start(ctx)
    enrich_obs(ctx, JOB_TYPE_PDF, article_id=42)

    try:
        raise RuntimeError("boom no processamento")
    except RuntimeError as e:
        record_job_failure(ctx, e)

    logs = finished_logs(log_records, status="failure")
    assert logs, "nenhum log estruturado de falha emitido"
    extra = logs[-1]["extra"]
    assert extra["job_type"] == JOB_TYPE_PDF
    assert extra["job_id"] == "job-abc123"
    assert extra["article_id"] == 42
    assert extra["attempt"] == 2
    assert extra["status"] == "failure"
    assert isinstance(extra["duration"], float)
    assert "RuntimeError" in str(extra["exception"])
    assert "boom no processamento" in str(extra["exception"])


async def test_record_job_failure_metrica_otel_quando_ativa(monkeypatch):
    import app.jobs.observe as observe

    failure = FakeCounter()
    monkeypatch.setattr(observe, "_job_failure_counter", failure)

    ctx = make_ctx()
    await on_job_start(ctx)
    enrich_obs(ctx, JOB_TYPE_PDF, article_id=42)
    record_job_failure(ctx, ValueError("x"))

    assert failure.adds == [(1, {"job_type": JOB_TYPE_PDF})]


# ---------------------------------------------------------------------------
# on_job_end: fecha sessão E registra resultado (fallback sem duplicar)
# ---------------------------------------------------------------------------


async def test_on_job_end_encerra_sessao_e_registra_sucesso(log_records):
    """T1.5 estende on_job_end: continua fechando a sessão e registra o job
    (fallback para jobs ainda não instrumentados)."""
    closed: list[bool] = []

    class Session:
        async def close(self):
            closed.append(True)

    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = Session()

    await on_job_end(ctx)

    assert closed == [True]  # sessão fechada (não regressão T1.4)
    assert "db" not in ctx  # sessão removida do ctx
    assert finished_logs(log_records, job_id="job-abc123", status="success")


async def test_on_job_end_registra_falha_quando_job_levantou_excecao(log_records):
    ctx = make_ctx(job_try=3)
    await on_job_start(ctx)
    ctx["db"] = None
    ctx["_job_obs"]["error"] = RuntimeError("falha no job")

    await on_job_end(ctx)

    logs = finished_logs(log_records, status="failure")
    assert logs, "on_job_end não registrou a falha"
    assert logs[-1]["extra"]["attempt"] == 3
    assert "falha no job" in str(logs[-1]["extra"]["exception"])


async def test_on_job_end_nao_registra_duas_vezes(log_records):
    """Job já registrado (decorator da task) não gera log duplicado no hook."""
    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = None
    enrich_obs(ctx, JOB_TYPE_PDF, article_id=1)
    record_job_success(ctx)

    await on_job_end(ctx)

    assert len(finished_logs(log_records, job_id="job-abc123")) == 1


async def test_on_job_end_sem_obs_nao_registra_nada(log_records):
    """on_job_end sem ctx de observabilidade apenas fecha a sessão."""
    ctx = make_ctx()
    await on_job_start(ctx)
    del ctx["_job_obs"]

    await on_job_end(ctx)

    assert finished_logs(log_records) == []
    assert "db" not in ctx


# ---------------------------------------------------------------------------
# Tasks decoradas: observabilidade fim-a-fim
# ---------------------------------------------------------------------------


class FakePDFService:
    @staticmethod
    async def process_article_pdf(article_id, pdf_url, db=None):  # noqa: ARG004
        return {"file_path": "/tmp/a.pdf", "file_hash": "h1"}


class BrokenPDFService:
    @staticmethod
    async def process_article_pdf(article_id, pdf_url, db=None):  # noqa: ARG004
        raise RuntimeError("pdf inválido")


async def test_task_download_pdf_registra_logs_de_inicio_e_sucesso(log_records, monkeypatch):
    monkeypatch.setattr("app.services.pdf_service.PDFService", FakePDFService)

    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = None

    result = await jobs_tasks.task_download_pdf(ctx, 9, "https://x/a.pdf")

    assert result["status"] == "processed"
    started = [
        r
        for r in log_records
        if r["message"] == "arq_job_started" and r["extra"].get("job_type") == JOB_TYPE_PDF
    ]
    assert started, "task não registrou início do job"
    assert started[-1]["extra"]["article_id"] == 9
    assert started[-1]["extra"]["attempt"] == 1

    logs = finished_logs(log_records, job_id="job-abc123", status="success")
    assert logs, "task não registrou conclusão do job"
    extra = logs[-1]["extra"]
    assert extra["job_type"] == JOB_TYPE_PDF
    assert extra["article_id"] == 9
    assert extra["attempt"] == 1
    assert isinstance(extra["duration"], float)


async def test_task_classify_article_registra_log_de_sucesso(log_records, monkeypatch):
    class FakeAIManager:
        async def classify(self, text):  # noqa: ARG002
            return ("autismo", 0.9)

    class FakeClassificationService:
        def __init__(self, db, ai_manager):  # noqa: ARG002
            pass

        async def classify_article(self, article_id):  # noqa: ARG002
            return ("autismo", 0.9)

    class Session:
        async def commit(self):
            pass

    monkeypatch.setattr("app.ai.get_ai_manager", lambda: FakeAIManager())
    monkeypatch.setattr(
        "app.services.classification_service.ClassificationService",
        FakeClassificationService,
    )

    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = Session()

    result = await jobs_tasks.task_classify_article(ctx, 5)

    assert result["category"] == "autismo"
    logs = finished_logs(log_records, job_id="job-abc123", status="success")
    assert logs, "task não registrou observabilidade"
    assert logs[-1]["extra"]["job_type"] == JOB_TYPE_CLASSIFY
    assert logs[-1]["extra"]["article_id"] == 5


async def test_task_que_levanta_excecao_registra_falha_antes_de_propagar(log_records, monkeypatch):
    """Exceção na task: falha registrada (com attempt) antes de propagar."""
    monkeypatch.setattr("app.services.pdf_service.PDFService", BrokenPDFService)

    ctx = make_ctx(job_try=2)
    await on_job_start(ctx)
    ctx["db"] = None

    with pytest.raises(RuntimeError, match="pdf inválido"):
        await jobs_tasks.task_download_pdf(ctx, 3, "https://x/b.pdf")

    logs = finished_logs(log_records, status="failure")
    assert logs, "exceção propagada sem registro de falha"
    extra = logs[-1]["extra"]
    assert extra["job_id"] == "job-abc123"
    assert extra["attempt"] == 2
    assert "pdf inválido" in str(extra["exception"])


async def test_job_executa_com_span_otel_quando_tracer_ativo(monkeypatch):
    """Com tracer ativo, a task roda dentro de um span arq.job com atributos."""
    import app.jobs.observe as observe

    tracer = FakeTracer()
    monkeypatch.setattr(observe, "_tracer", tracer)
    monkeypatch.setattr("app.services.pdf_service.PDFService", FakePDFService)

    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = None

    await jobs_tasks.task_download_pdf(ctx, 9, "https://x/a.pdf")

    assert tracer.started == ["arq.job"]
    span = tracer.span
    assert span.attributes["job.type"] == JOB_TYPE_PDF
    assert span.attributes["job.id"] == "job-abc123"
    assert span.attributes["job.article_id"] == 9
    assert span.attributes["job.attempt"] == 1
    assert span.attributes["job.status"] == "success"
    assert span.ended
    assert span.status_calls  # status explícito no span


async def test_job_com_falha_registra_exception_no_span(monkeypatch):
    import app.jobs.observe as observe

    tracer = FakeTracer()
    monkeypatch.setattr(observe, "_tracer", tracer)
    monkeypatch.setattr("app.services.pdf_service.PDFService", BrokenPDFService)

    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = None

    with pytest.raises(RuntimeError):
        await jobs_tasks.task_download_pdf(ctx, 3, "https://x/b.pdf")

    span = tracer.span
    assert span.attributes["job.status"] == "failure"
    assert isinstance(span.recorded_exception, RuntimeError)
    assert span.ended


async def test_span_esta_ativo_durante_a_execucao_do_job(monkeypatch):
    """O span arq.job precisa cobrir a execução do job, não só o registro
    final — start_as_current_span envolve a chamada da task."""
    import app.jobs.observe as observe

    tracer = FakeTracer()
    monkeypatch.setattr(observe, "_tracer", tracer)

    seen: dict[str, Any] = {}

    class Service:
        @staticmethod
        async def process_article_pdf(article_id, pdf_url, db=None):  # noqa: ARG004
            seen["spans_ativos"] = list(tracer.started)
            return {"file_path": "/tmp/a.pdf", "file_hash": "h1"}

    monkeypatch.setattr("app.services.pdf_service.PDFService", Service)

    ctx = make_ctx()
    await on_job_start(ctx)
    ctx["db"] = None

    await jobs_tasks.task_download_pdf(ctx, 9, "https://x/a.pdf")

    assert seen["spans_ativos"] == ["arq.job"]


# ---------------------------------------------------------------------------
# Worker: startup inicializa telemetria; settings intactos
# ---------------------------------------------------------------------------


async def test_worker_startup_inicializa_telemetria_do_worker(monkeypatch):
    import app.core.telemetry as telemetry_mod
    from app.jobs import observe
    from app.jobs.tasks import startup

    monkeypatch.setattr(settings, "enable_telemetry", True)
    monkeypatch.setattr("app.ml.EmbeddingClassifier", None)

    calls: list[Any] = []
    monkeypatch.setattr(
        telemetry_mod, "setup_telemetry", lambda name: calls.append(("setup", name))
    )
    monkeypatch.setattr(observe, "init_job_telemetry", lambda: calls.append(("init",)))

    ctx: dict[str, Any] = {}
    await startup(ctx)

    assert ("setup", settings.telemetry_service_name) in calls
    assert ("init",) in calls
    assert "session_factory" in ctx


async def test_worker_startup_sem_telemetria_nao_configura_provider(monkeypatch):
    import app.core.telemetry as telemetry_mod
    from app.jobs.tasks import startup

    monkeypatch.setattr(settings, "enable_telemetry", False)
    monkeypatch.setattr("app.ml.EmbeddingClassifier", None)

    calls: list[Any] = []
    monkeypatch.setattr(telemetry_mod, "setup_telemetry", lambda name: calls.append(name))

    await startup({})

    assert calls == []  # provider só é configurado quando a telemetria está ativa


def test_worker_settings_mantem_hooks_e_retry():
    assert WorkerSettings.on_job_start is on_job_start
    assert WorkerSettings.on_job_end is on_job_end
    assert WorkerSettings.max_tries == 3
    assert WorkerSettings.retry_jobs is True
