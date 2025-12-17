"""
Schemas para analytics.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.analytics import EventType, SessionStatus
from app.schemas.common import BaseSchema


class AnalyticsEventCreate(BaseModel):
    """Schema para criação de evento."""

    event_type: EventType
    event_name: str = Field(..., max_length=255)
    properties: dict[str, Any] | None = None
    page_path: str | None = Field(None, max_length=500)
    referrer: str | None = Field(None, max_length=500)


class AnalyticsEventResponse(BaseSchema):
    """Schema de resposta de evento."""

    id: int
    session_id: str
    user_id: int | None
    event_type: EventType
    event_name: str
    properties: dict[str, Any]
    page_path: str | None
    timestamp: datetime


class AnalyticsSessionResponse(BaseSchema):
    """Schema de resposta de sessão."""

    id: int
    session_id: str
    user_id: int | None
    status: SessionStatus
    device_type: str | None
    browser: str | None
    os: str | None
    started_at: datetime
    ended_at: datetime | None
    page_views: int
    events_count: int
    duration_seconds: int | None


class TrafficStatsResponse(BaseSchema):
    """Estatísticas de tráfego."""

    total_sessions: int
    unique_visitors: int
    total_page_views: int
    avg_session_duration: float


class ContentStatsResponse(BaseSchema):
    """Estatísticas de conteúdo."""

    article_views: int
    article_downloads: int
    searches: int


class EventsStatsResponse(BaseSchema):
    """Estatísticas de eventos."""

    total_events: int
    events_by_type: dict[str, int]


class TimeSeriesDataPoint(BaseSchema):
    """Ponto de dados de série temporal."""

    period: str
    count: int


class TopPageResponse(BaseSchema):
    """Página mais visitada."""

    path: str
    views: int


class AnalyticsOverviewResponse(BaseSchema):
    """Visão geral de analytics."""

    traffic: TrafficStatsResponse
    content: ContentStatsResponse
    events: EventsStatsResponse
    time_series: list[TimeSeriesDataPoint]
    top_pages: list[TopPageResponse]
    period_days: int

