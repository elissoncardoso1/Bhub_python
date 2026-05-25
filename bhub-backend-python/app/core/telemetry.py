"""Configuração e helpers mínimos de OpenTelemetry."""

from __future__ import annotations

from app.core.logging import log

ai_latency = None
ai_fallback_counter = None
feed_ingested_counter = None
feed_failed_counter = None


def setup_telemetry(app_name: str = "bhub-backend") -> None:
    """Configura traces e métricas quando as dependências estiverem disponíveis."""
    global ai_latency, ai_fallback_counter, feed_ingested_counter, feed_failed_counter

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        log.warning(f"OpenTelemetry não disponível: {e}")
        return

    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metrics.set_meter_provider(MeterProvider())
    meter = metrics.get_meter(app_name)

    ai_latency = meter.create_histogram(
        "ai.classify.duration_ms",
        description="Latência de classificação por provedor",
        unit="ms",
    )
    ai_fallback_counter = meter.create_counter(
        "ai.fallback.total",
        description="Total de fallbacks entre provedores de IA",
    )
    feed_ingested_counter = meter.create_counter(
        "feeds.articles.ingested.total",
        description="Total de artigos ingeridos por feeds",
    )
    feed_failed_counter = meter.create_counter(
        "feeds.sync.failed.total",
        description="Total de sincronizações de feed com falha",
    )


def record_ai_latency(duration_ms: float, provider: str) -> None:
    if ai_latency:
        ai_latency.record(duration_ms, {"provider": provider})


def record_ai_fallback(provider: str) -> None:
    if ai_fallback_counter:
        ai_fallback_counter.add(1, {"from": provider})


def record_feed_ingested(count: int, feed_name: str) -> None:
    if feed_ingested_counter and count:
        feed_ingested_counter.add(count, {"feed": feed_name})


def record_feed_failed(feed_name: str) -> None:
    if feed_failed_counter:
        feed_failed_counter.add(1, {"feed": feed_name})
