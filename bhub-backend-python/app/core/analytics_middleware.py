"""
Middleware para captura automática de eventos de analytics.
Respeita privacidade e não coleta dados pessoais identificáveis.
"""

import hashlib
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.models.analytics import EventType
from app.services.analytics_service import AnalyticsService
from app.database import get_session_context
from app.config import settings


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware que captura automaticamente eventos de analytics.
    Registra page views e requisições da API de forma transparente.
    """

    def __init__(self, app: ASGIApp, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        # Rotas que não devem ser rastreadas
        self.excluded_paths = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/analytics/track",
            "/api/v1/analytics/pageview",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processa a requisição e registra eventos de analytics."""
        if not self.enabled:
            return await call_next(request)

        # Verificar Do Not Track header se configurado
        if settings.analytics_respect_dnt and request.headers.get("DNT") == "1":
            return await call_next(request)

        # Verificar se a rota deve ser rastreada
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Gerar ou obter session_id
        session_id = self._get_or_create_session_id(request)

        # Processar requisição
        start_time = datetime.utcnow()
        response = await call_next(request)
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Registrar evento em background (não bloquear resposta)
        if response.status_code < 400:  # Apenas sucessos
            try:
                await self._track_request(
                    request=request,
                    response=response,
                    session_id=session_id,
                    duration=duration,
                )
            except Exception:
                # Não falhar a requisição se analytics falhar
                pass

        # Adicionar session_id no header da resposta
        response.headers["X-Session-ID"] = session_id

        return response

    def _get_or_create_session_id(self, request: Request) -> str:
        """Obtém ou cria um session_id para o usuário."""
        # Tentar obter do header
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id

        # Tentar obter do cookie
        session_id = request.cookies.get("analytics_session_id")
        if session_id:
            return session_id

        # Gerar novo session_id
        ip = request.client.host if request.client else None
        user_id = None  # Poderia extrair de token JWT se autenticado
        return AnalyticsService.generate_session_id(user_id=user_id, ip=ip)

    async def _track_request(
        self,
        request: Request,
        response: Response,
        session_id: str,
        duration: float,
    ) -> None:
        """Registra uma requisição como evento de analytics."""
        # Determinar tipo de evento
        path = request.url.path

        if path.startswith("/api/v1"):
            event_type = EventType.API_REQUEST
            event_name = f"{request.method} {path}"
        else:
            event_type = EventType.PAGE_VIEW
            event_name = "page_view"

        # Propriedades do evento
        properties = {
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }

        # Obter referrer
        referrer = request.headers.get("referer") or request.headers.get("referrer")

        # Registrar evento
        async with get_session_context() as db:
            # Anonimizar IP para compliance LGPD/GDPR
            from app.core.ip_anonymization import anonymize_ip, should_anonymize_ip
            
            raw_ip = request.client.host if request.client else None
            ip_address = anonymize_ip(raw_ip) if should_anonymize_ip() else raw_ip
            
            # Obter ou criar sessão
            await AnalyticsService.get_or_create_session(
                db=db,
                session_id=session_id,
                user_agent=request.headers.get("user-agent"),
                ip_address=ip_address,
            )

            # Registrar evento
            await AnalyticsService.track_event(
                db=db,
                event_type=event_type,
                event_name=event_name,
                session_id=session_id,
                properties=properties,
                page_path=path,
                referrer=referrer,
                user_agent=request.headers.get("user-agent"),
                ip_address=ip_address,
            )

            await db.commit()

