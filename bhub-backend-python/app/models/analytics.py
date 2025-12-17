"""
Modelos de analytics para rastreamento de eventos e métricas.
"""

import enum
import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class EventType(str, enum.Enum):
    """Tipos de eventos rastreados."""

    PAGE_VIEW = "page_view"
    ARTICLE_VIEW = "article_view"
    ARTICLE_DOWNLOAD = "article_download"
    SEARCH = "search"
    FILTER = "filter"
    CATEGORY_CLICK = "category_click"
    FEED_CLICK = "feed_click"
    AUTHOR_CLICK = "author_click"
    PDF_UPLOAD = "pdf_upload"
    FEED_SYNC = "feed_sync"
    ERROR = "error"
    API_REQUEST = "api_request"


class SessionStatus(str, enum.Enum):
    """Status da sessão."""

    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"


class AnalyticsEvent(BaseModel):
    """
    Evento de analytics individual.
    """

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identificação
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType), nullable=False, index=True
    )

    # Dados do evento
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string

    # Contexto
    page_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, default=datetime.utcnow
    )

    # Índices compostos
    __table_args__ = (
        Index("ix_analytics_events_type_timestamp", "event_type", "timestamp"),
        Index("ix_analytics_events_session_timestamp", "session_id", "timestamp"),
    )

    def set_properties(self, props: dict[str, Any]) -> None:
        """Define propriedades do evento como JSON."""
        self.properties = json.dumps(props) if props else None

    def get_properties(self) -> dict[str, Any]:
        """Retorna propriedades do evento como dict."""
        if not self.properties:
            return {}
        try:
            return json.loads(self.properties)
        except (json.JSONDecodeError, TypeError):
            return {}


class AnalyticsSession(BaseModel):
    """
    Sessão de analytics do usuário.
    """

    __tablename__ = "analytics_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identificação
    session_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Dados da sessão
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True
    )
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Métricas
    page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AnalyticsMetric(BaseModel):
    """
    Métricas agregadas por período.
    """

    __tablename__ = "analytics_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Período
    metric_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'hour', 'day', 'week', 'month'

    # Métricas de tráfego
    total_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Métricas de conteúdo
    article_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    article_downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    searches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Métricas de engajamento
    avg_session_duration: Mapped[float | None] = mapped_column(
        Integer, nullable=True
    )  # em segundos
    bounce_rate: Mapped[float | None] = mapped_column(Integer, nullable=True)  # porcentagem

    # Índices compostos
    __table_args__ = (
        Index("ix_analytics_metrics_date_period", "metric_date", "period_type"),
    )

