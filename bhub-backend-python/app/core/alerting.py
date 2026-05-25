"""
Alertas mínimos via webhook (opcional).
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

from app.core.log_sanitizer import sanitize_for_logging


def create_alert_sink(webhook_url: str, timeout_seconds: int) -> Callable:
    """
    Retorna um sink do Loguru que envia alertas para um webhook.

    O envio é best-effort para não interromper o fluxo principal.
    """
    client = httpx.Client(timeout=timeout_seconds)

    def _sink(message) -> None:
        record = message.record
        payload = {
            "level": record["level"].name,
            "message": record["message"],
            "timestamp": record["time"].isoformat(),
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "exception": str(record["exception"]) if record["exception"] else None,
        }
        payload = sanitize_for_logging(payload)
        try:
            client.post(webhook_url, json=payload)
        except Exception:
            # Não propagar erros de alertas para não quebrar o app.
            pass

    return _sink
