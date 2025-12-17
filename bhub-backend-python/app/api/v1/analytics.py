"""
Rotas públicas de analytics (para tracking de eventos).
"""

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.api.deps import DBSession
from app.models.analytics import EventType
from app.schemas.analytics import AnalyticsEventCreate
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/track")
async def track_event(
    request: Request,
    db: DBSession,
    event: AnalyticsEventCreate,
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
):
    """
    Endpoint público para rastreamento de eventos.
    Respeita privacidade e não coleta dados pessoais identificáveis.
    """
    # Gerar ou usar session_id fornecido
    session_id = x_session_id or AnalyticsService.generate_session_id(
        ip=request.client.host if request.client else None
    )

    # Obter ou criar sessão
    await AnalyticsService.get_or_create_session(
        db=db,
        session_id=session_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # Registrar evento
    await AnalyticsService.track_event(
        db=db,
        event_type=event.event_type,
        event_name=event.event_name,
        session_id=session_id,
        properties=event.properties,
        page_path=event.page_path,
        referrer=event.referrer,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    await db.commit()

    return JSONResponse(
        content={"success": True, "session_id": session_id},
        status_code=200,
    )


@router.post("/pageview")
async def track_pageview(
    request: Request,
    db: DBSession,
    page_path: str,
    referrer: str | None = None,
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
):
    """
    Endpoint simplificado para rastreamento de visualizações de página.
    """
    session_id = x_session_id or AnalyticsService.generate_session_id(
        ip=request.client.host if request.client else None
    )

    # Obter ou criar sessão e incrementar page views
    session = await AnalyticsService.get_or_create_session(
        db=db,
        session_id=session_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    session.page_views += 1

    # Registrar evento
    await AnalyticsService.track_event(
        db=db,
        event_type=EventType.PAGE_VIEW,
        event_name="page_view",
        session_id=session_id,
        properties={"page_path": page_path, "referrer": referrer},
        page_path=page_path,
        referrer=referrer,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    await db.commit()

    return JSONResponse(
        content={"success": True, "session_id": session_id},
        status_code=200,
    )

