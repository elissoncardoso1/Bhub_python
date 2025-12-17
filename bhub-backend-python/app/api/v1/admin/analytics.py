"""
Rotas admin de analytics.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession
from app.core import CurrentAdmin
from app.models.analytics import EventType
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    ContentStatsResponse,
    EventsStatsResponse,
    TimeSeriesDataPoint,
    TopPageResponse,
    TrafficStatsResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Admin - Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    db: DBSession,
    admin: CurrentAdmin,
    days: int = Query(default=30, ge=1, le=365, description="Período em dias"),
):
    """Retorna visão geral de analytics."""
    traffic = await AnalyticsService.get_traffic_stats(db, days=days)
    content = await AnalyticsService.get_content_stats(db, days=days)
    events = await AnalyticsService.get_events_stats(db)
    time_series = await AnalyticsService.get_time_series_data(db, days=days, period="day")
    top_pages = await AnalyticsService.get_top_pages(db, days=days, limit=10)

    return AnalyticsOverviewResponse(
        traffic=TrafficStatsResponse(**traffic),
        content=ContentStatsResponse(**content),
        events=EventsStatsResponse(**events),
        time_series=[TimeSeriesDataPoint(**item) for item in time_series],
        top_pages=[TopPageResponse(**item) for item in top_pages],
        period_days=days,
    )


@router.get("/traffic", response_model=TrafficStatsResponse)
async def get_traffic_stats(
    db: DBSession,
    admin: CurrentAdmin,
    days: int = Query(default=30, ge=1, le=365),
):
    """Retorna estatísticas de tráfego."""
    stats = await AnalyticsService.get_traffic_stats(db, days=days)
    return TrafficStatsResponse(**stats)


@router.get("/content", response_model=ContentStatsResponse)
async def get_content_stats(
    db: DBSession,
    admin: CurrentAdmin,
    days: int = Query(default=30, ge=1, le=365),
):
    """Retorna estatísticas de conteúdo."""
    stats = await AnalyticsService.get_content_stats(db, days=days)
    return ContentStatsResponse(**stats)


@router.get("/events", response_model=EventsStatsResponse)
async def get_events_stats(
    db: DBSession,
    admin: CurrentAdmin,
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    event_type: EventType | None = Query(default=None),
):
    """Retorna estatísticas de eventos."""
    stats = await AnalyticsService.get_events_stats(
        db, start_date=start_date, end_date=end_date, event_type=event_type
    )
    return EventsStatsResponse(**stats)


@router.get("/time-series", response_model=list[TimeSeriesDataPoint])
async def get_time_series_data(
    db: DBSession,
    admin: CurrentAdmin,
    days: int = Query(default=30, ge=1, le=365),
    period: str = Query(default="day", pattern="^(hour|day|week|month)$"),
):
    """Retorna dados de série temporal."""
    data = await AnalyticsService.get_time_series_data(db, days=days, period=period)
    return [TimeSeriesDataPoint(**item) for item in data]


@router.get("/top-pages", response_model=list[TopPageResponse])
async def get_top_pages(
    db: DBSession,
    admin: CurrentAdmin,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Retorna páginas mais visitadas."""
    pages = await AnalyticsService.get_top_pages(db, days=days, limit=limit)
    return [TopPageResponse(**item) for item in pages]

