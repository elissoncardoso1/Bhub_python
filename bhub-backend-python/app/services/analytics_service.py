"""
Serviço de analytics para coleta e análise de dados.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    AnalyticsEvent,
    AnalyticsMetric,
    AnalyticsSession,
    EventType,
    SessionStatus,
)


class AnalyticsService:
    """Serviço para gerenciar analytics."""

    @staticmethod
    def generate_session_id(user_id: int | None = None, ip: str | None = None) -> str:
        """Gera um ID único de sessão."""
        timestamp = datetime.utcnow().isoformat()
        data = f"{timestamp}-{user_id or 'anonymous'}-{ip or 'unknown'}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    @staticmethod
    async def track_event(
        db: AsyncSession,
        event_type: EventType,
        event_name: str,
        session_id: str,
        properties: dict[str, Any] | None = None,
        user_id: int | None = None,
        page_path: str | None = None,
        referrer: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AnalyticsEvent:
        """Registra um evento de analytics."""
        event = AnalyticsEvent(
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            event_name=event_name,
            page_path=page_path,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        event.set_properties(properties or {})

        db.add(event)
        await db.flush()

        # Atualizar contador de eventos da sessão
        await AnalyticsService._update_session_events_count(db, session_id)

        return event

    @staticmethod
    async def _update_session_events_count(
        db: AsyncSession, session_id: str
    ) -> None:
        """Atualiza contador de eventos da sessão."""
        session = await db.scalar(
            select(AnalyticsSession).where(
                AnalyticsSession.session_id == session_id
            )
        )
        if session:
            session.events_count += 1
            session.last_activity = datetime.utcnow()

    @staticmethod
    async def get_or_create_session(
        db: AsyncSession,
        session_id: str,
        user_id: int | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AnalyticsSession:
        """Obtém ou cria uma sessão de analytics."""
        session = await db.scalar(
            select(AnalyticsSession).where(
                AnalyticsSession.session_id == session_id
            )
        )

        if not session:
            # Extrair informações do user agent
            device_type, browser, os = AnalyticsService._parse_user_agent(
                user_agent or ""
            )

            session = AnalyticsSession(
                session_id=session_id,
                user_id=user_id,
                status=SessionStatus.ACTIVE,
                device_type=device_type,
                browser=browser,
                os=os,
                started_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
            )
            db.add(session)
            await db.flush()
        else:
            # Atualizar última atividade
            session.last_activity = datetime.utcnow()

        return session

    @staticmethod
    def _parse_user_agent(user_agent: str) -> tuple[str | None, str | None, str | None]:
        """Extrai informações básicas do user agent."""
        if not user_agent:
            return None, None, None

        ua_lower = user_agent.lower()

        # Detectar dispositivo
        device_type = None
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"
        else:
            device_type = "desktop"

        # Detectar navegador
        browser = None
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "Chrome"
        elif "firefox" in ua_lower:
            browser = "Firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "Safari"
        elif "edg" in ua_lower:
            browser = "Edge"
        elif "opera" in ua_lower:
            browser = "Opera"

        # Detectar OS
        os_name = None
        if "windows" in ua_lower:
            os_name = "Windows"
        elif "mac" in ua_lower or "darwin" in ua_lower:
            os_name = "macOS"
        elif "linux" in ua_lower:
            os_name = "Linux"
        elif "android" in ua_lower:
            os_name = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower:
            os_name = "iOS"

        return device_type, browser, os_name

    @staticmethod
    async def end_session(
        db: AsyncSession, session_id: str, duration: int | None = None
    ) -> None:
        """Finaliza uma sessão."""
        session = await db.scalar(
            select(AnalyticsSession).where(
                AnalyticsSession.session_id == session_id
            )
        )
        if session and session.status == SessionStatus.ACTIVE:
            session.status = SessionStatus.ENDED
            session.ended_at = datetime.utcnow()
            if duration:
                session.duration_seconds = duration

    @staticmethod
    async def get_events_stats(
        db: AsyncSession,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_type: EventType | None = None,
    ) -> dict[str, Any]:
        """Retorna estatísticas de eventos."""
        stmt = select(AnalyticsEvent)

        if start_date:
            stmt = stmt.where(AnalyticsEvent.timestamp >= start_date)
        if end_date:
            stmt = stmt.where(AnalyticsEvent.timestamp <= end_date)
        if event_type:
            stmt = stmt.where(AnalyticsEvent.event_type == event_type)

        # Total de eventos
        total = await db.scalar(
            select(func.count()).select_from(stmt.subquery())
        ) or 0

        # Eventos por tipo
        type_stats = await db.execute(
            select(
                AnalyticsEvent.event_type,
                func.count(AnalyticsEvent.id).label("count"),
            )
            .where(
                (AnalyticsEvent.timestamp >= start_date if start_date else True)
                & (AnalyticsEvent.timestamp <= end_date if end_date else True)
            )
            .group_by(AnalyticsEvent.event_type)
        )

        events_by_type = {
            row[0].value: row[1] for row in type_stats.fetchall()
        }

        return {
            "total_events": total,
            "events_by_type": events_by_type,
        }

    @staticmethod
    async def get_traffic_stats(
        db: AsyncSession,
        days: int = 30,
    ) -> dict[str, Any]:
        """Retorna estatísticas de tráfego."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total de sessões
        total_sessions = await db.scalar(
            select(func.count()).select_from(
                select(AnalyticsSession).where(
                    AnalyticsSession.started_at >= start_date
                ).subquery()
            )
        ) or 0

        # Sessões únicas (por user_id ou session_id)
        unique_visitors = await db.scalar(
            select(func.count(func.distinct(AnalyticsSession.user_id)))
            .where(AnalyticsSession.started_at >= start_date)
        ) or 0

        # Total de page views
        total_page_views = await db.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.event_type == EventType.PAGE_VIEW,
                AnalyticsEvent.timestamp >= start_date,
            )
        ) or 0

        # Média de duração de sessão
        avg_duration = await db.scalar(
            select(func.avg(AnalyticsSession.duration_seconds))
            .where(
                AnalyticsSession.started_at >= start_date,
                AnalyticsSession.duration_seconds.isnot(None),
            )
        ) or 0

        return {
            "total_sessions": total_sessions,
            "unique_visitors": unique_visitors,
            "total_page_views": total_page_views,
            "avg_session_duration": round(avg_duration, 2) if avg_duration else 0,
        }

    @staticmethod
    async def get_content_stats(
        db: AsyncSession,
        days: int = 30,
    ) -> dict[str, Any]:
        """Retorna estatísticas de conteúdo."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Visualizações de artigos
        article_views = await db.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.event_type == EventType.ARTICLE_VIEW,
                AnalyticsEvent.timestamp >= start_date,
            )
        ) or 0

        # Downloads de artigos
        article_downloads = await db.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.event_type == EventType.ARTICLE_DOWNLOAD,
                AnalyticsEvent.timestamp >= start_date,
            )
        ) or 0

        # Buscas
        searches = await db.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.event_type == EventType.SEARCH,
                AnalyticsEvent.timestamp >= start_date,
            )
        ) or 0

        return {
            "article_views": article_views,
            "article_downloads": article_downloads,
            "searches": searches,
        }

    @staticmethod
    async def get_time_series_data(
        db: AsyncSession,
        days: int = 30,
        period: str = "day",
    ) -> list[dict[str, Any]]:
        """Retorna dados de série temporal."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Agrupar por período
        if period == "hour":
            date_format = "%Y-%m-%d %H:00:00"
        elif period == "day":
            date_format = "%Y-%m-%d"
        elif period == "week":
            date_format = "%Y-W%V"
        else:  # month
            date_format = "%Y-%m"

        # Query para eventos por período
        stmt = (
            select(
                func.strftime(date_format, AnalyticsEvent.timestamp).label("period"),
                func.count(AnalyticsEvent.id).label("count"),
            )
            .where(AnalyticsEvent.timestamp >= start_date)
            .group_by("period")
            .order_by("period")
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        return [{"period": row[0], "count": row[1]} for row in rows]

    @staticmethod
    async def get_top_pages(
        db: AsyncSession,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retorna páginas mais visitadas."""
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(
                AnalyticsEvent.page_path,
                func.count(AnalyticsEvent.id).label("views"),
            )
            .where(
                AnalyticsEvent.event_type == EventType.PAGE_VIEW,
                AnalyticsEvent.timestamp >= start_date,
                AnalyticsEvent.page_path.isnot(None),
            )
            .group_by(AnalyticsEvent.page_path)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        return [{"path": row[0], "views": row[1]} for row in rows]

