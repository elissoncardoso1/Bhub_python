"""
Middleware para captura automática de eventos de analytics.
Respeita privacidade e não coleta dados pessoais identificáveis.
"""

from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings
from app.core.cookie_consent import is_granted
from app.database import get_session_context
from app.models.analytics import EventType
from app.services.analytics_service import AnalyticsService

# Nome do cookie de sessão de analytics — compartilhado com app/web/consent.py
# (que o apaga quando o visitante revoga/nega a categoria "analytics").
ANALYTICS_SESSION_COOKIE = "analytics_session_id"

# Prefixos de rota que NUNCA são rastreados (mesmo com consentimento)
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "/admin",
    "/login",
    "/logout",
    "/api/v1/auth",
    "/api/v1/contact",
    "/contact",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
    "/api/v1/analytics",
    "/api/v1/cookie-consent",
    "/cookie-consent",
    "/privacy",
    "/cookies",
    "/terms",
)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware que captura automaticamente eventos de analytics.
    Registra page views e requisições da API de forma transparente.

    Registrado incondicionalmente em app/main.py; o gate abaixo decide, por
    requisição, se algo é de fato coletado: config habilitada (`enable_analytics`)
    E consentimento concedido para a categoria "analytics" E DNT != 1 E rota
    não excluída (`EXCLUDED_PREFIXES`).
    """

    def _is_excluded(self, path: str) -> bool:
        """Comparação segura de prefixo: /contact exclui /contact/x, não /contactos."""
        return any(path == p or path.startswith(p + "/") for p in EXCLUDED_PREFIXES)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Processa a requisição e registra eventos de analytics."""
        if not settings.enable_analytics:
            return await call_next(request)

        # Verificar Do Not Track header se configurado
        if settings.analytics_respect_dnt and request.headers.get("DNT") == "1":
            return await call_next(request)

        if not is_granted(request, "analytics"):
            return await call_next(request)

        # Verificar se a rota deve ser rastreada
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # Gerar ou obter session_id
        had_session = bool(
            request.headers.get("X-Session-ID") or request.cookies.get(ANALYTICS_SESSION_COOKIE)
        )
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

        # Persistir session_id em cookie para SSR/HTMX (não depende de header no client)
        if not had_session:
            response.set_cookie(
                key=ANALYTICS_SESSION_COOKIE,
                value=session_id,
                httponly=True,
                secure=not settings.is_development,
                samesite="lax",
                max_age=3600 * 24 * 30,  # 30 dias
                path="/",
            )

        return response

    def _get_or_create_session_id(self, request: Request) -> str:
        """Obtém ou cria um session_id para o usuário."""
        # Tentar obter do header
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id

        # Tentar obter do cookie
        session_id = request.cookies.get(ANALYTICS_SESSION_COOKIE)
        if session_id:
            return session_id

        # Gerar novo session_id
        return AnalyticsService.generate_session_id()

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
