"""Observabilidade dos jobs ARQ (T1.5 — plano BHub v1.1).

Todo job do worker registra um log estruturado com:

    job_type, job_id, article_id, attempt, status, duration, exception

Quando o OpenTelemetry está ativo (``init_job_telemetry`` chamado no
startup do worker), também são emitidos:

    arq.job.success   (contador)
    arq.job.failure   (contador)
    arq.job.duration  (histograma, segundos)
    span "arq.job"    (com atributos job.* e status/exception)

Segue o padrão de ``app.core.telemetry``: globais ``None`` quando a
telemetria não está configurada e os helpers fazem no-op nesses casos —
observabilidade nunca derruba o processamento do job.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

_tracer: Any = None
_job_success_counter: Any = None
_job_failure_counter: Any = None
_job_duration_histogram: Any = None

JOB_TYPE_CLASSIFY = "task_classify_article"
JOB_TYPE_DOWNLOAD_PDF = "task_download_pdf"

_OBS_KEY = "_job_obs"


def init_job_telemetry() -> None:
    """Cria métricas do OTel a partir do meter já configurado por setup_telemetry."""
    global _job_success_counter, _job_failure_counter, _job_duration_histogram

    try:
        from opentelemetry import metrics, trace
    except ImportError:
        return

    try:
        meter = metrics.get_meter("bhub-arq-jobs")
        _job_success_counter = meter.create_counter(
            "arq.job.success",
            description="Total de jobs ARQ concluídos com sucesso",
        )
        _job_failure_counter = meter.create_counter(
            "arq.job.failure",
            description="Total de jobs ARQ finalizados com falha",
        )
        _job_duration_histogram = meter.create_histogram(
            "arq.job.duration",
            description="Duração dos jobs ARQ em segundos",
            unit="s",
        )
        _set_tracer(trace.get_tracer("bhub-arq-jobs"))
    except Exception as e:  # pragma: no cover — defesa contra provider não configurado
        logger.warning(f"telemetria de jobs não inicializada: {e}")


def _set_tracer(tracer: Any) -> None:
    global _tracer
    _tracer = tracer


def init_job_obs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cria (ou recupera) o contexto de observabilidade do job no ctx.

    O worker ARQ 0.28 fornece ``job_id`` e ``job_try`` no ctx passado aos
    hooks ``on_job_start``/``on_job_end`` e às próprias funções de job.
    """
    obs = ctx.get(_OBS_KEY)
    if obs is None:
        obs = {
            "job_type": None,
            "job_id": ctx.get("job_id"),
            "article_id": None,
            "attempt": ctx.get("job_try", 1) or 1,
            "start": time.perf_counter(),
            "error": None,
            "recorded": False,
        }
        ctx[_OBS_KEY] = obs
    return obs


def enrich_job_obs(
    ctx: dict[str, Any],
    job_type: str,
    article_id: int | None,
) -> None:
    """Preenche job_type/article_id — chamado pelo decorator @observed_job."""
    obs = init_job_obs(ctx)
    obs["job_type"] = job_type
    obs["article_id"] = article_id


def _log_finished(
    obs: dict[str, Any],
    status: str,
    duration: float,
    exception: BaseException | None,
) -> None:
    extra: dict[str, Any] = {
        "job_type": obs.get("job_type"),
        "job_id": obs.get("job_id"),
        "article_id": obs.get("article_id"),
        "attempt": obs.get("attempt"),
        "status": status,
        "duration": duration,
    }
    if exception is not None:
        extra["exception"] = f"{type(exception).__name__}: {exception}"

    level = "ERROR" if status == "failure" else "INFO"
    logger.bind(**extra).log(level, "arq_job_finished")


def _otel_metrics(
    obs: dict[str, Any],
    status: str,
    duration: float,
) -> None:
    """Métricas OTel — cada uma é opcional (padrão telemetry.py)."""
    attributes = {"job_type": obs.get("job_type")}
    try:
        if status == "failure":
            if _job_failure_counter:
                _job_failure_counter.add(1, attributes)
        elif _job_success_counter:
            _job_success_counter.add(1, attributes)
        if _job_duration_histogram:
            _job_duration_histogram.record(duration, attributes)
    except Exception as e:  # pragma: no cover — observabilidade nunca quebra o job
        logger.warning(f"telemetria de job falhou (ignorado): {e}")


def _span_attributes(span: Any, obs: dict[str, Any], status: str) -> None:
    span.set_attribute("job.type", obs.get("job_type"))
    span.set_attribute("job.id", obs.get("job_id"))
    if obs.get("article_id") is not None:
        span.set_attribute("job.article_id", obs["article_id"])
    span.set_attribute("job.attempt", obs.get("attempt"))
    span.set_attribute("job.status", status)


def _finish_span(span: Any, obs: dict[str, Any], status: str) -> None:
    """Conclui o span do job com status e exception (quando houver)."""
    from opentelemetry.trace import Status, StatusCode

    _span_attributes(span, obs, status)
    if status == "failure":
        span.set_status(Status(StatusCode.ERROR))
    else:
        span.set_status(Status(StatusCode.OK))
    span.end()


def record_job_success(ctx: dict[str, Any]) -> None:
    """Registra conclusão bem-sucedida do job (log + métricas OTel)."""
    obs = init_job_obs(ctx)
    duration = time.perf_counter() - obs["start"]
    _log_finished(obs, "success", duration, None)
    _otel_metrics(obs, "success", duration)
    obs["recorded"] = True


def record_job_failure(ctx: dict[str, Any], exception: BaseException) -> None:
    """Registra falha do job (log + métricas OTel)."""
    obs = init_job_obs(ctx)
    duration = time.perf_counter() - obs["start"]
    _log_finished(obs, "failure", duration, exception)
    _otel_metrics(obs, "failure", duration)
    obs["recorded"] = True


def observed_job(
    job_type: str,
    article_id_arg: str = "article_id",
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator de observabilidade para funções de job do worker.

    Registra início, sucesso/falha, duração e exceção de cada execução.
    A exceção é sempre re-levantada — o retry do ARQ decide o resto.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapped(ctx: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
            article_id = kwargs.get(article_id_arg)
            if article_id is None and args:
                article_id = args[0]

            enrich_job_obs(ctx, job_type, article_id)
            obs = init_job_obs(ctx)

            logger.bind(
                job_type=job_type,
                job_id=obs["job_id"],
                article_id=article_id,
                attempt=obs["attempt"],
            ).info("arq_job_started")

            span_cm = (
                _tracer.start_as_current_span("arq.job")
                if _tracer
                else _NullSpan()
            )
            with span_cm as span:
                try:
                    result = await func(ctx, *args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    _finish_span(span, obs, "failure")
                    record_job_failure(ctx, e)
                    raise
                _finish_span(span, obs, "success")
                record_job_success(ctx)
                return result

        return wrapped

    return decorator


class _NullSpan:
    """Context manager neutro quando não há tracer OTel ativo."""

    def __enter__(self):
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def end(self) -> None:
        pass
