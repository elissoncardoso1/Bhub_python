"""
Middleware para adicionar security headers HTTP.
Protege a aplicação contra vários tipos de ataques.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona security headers HTTP à resposta.
    
    Headers incluídos:
    - Strict-Transport-Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - Content-Security-Policy (configurável)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.csp_policy = self._build_csp_policy()

    def _build_csp_policy(self) -> str:
        """
        Constrói a política Content-Security-Policy.
        Pode ser customizada via variáveis de ambiente.
        """
        # Política base
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Next.js precisa de unsafe-inline
            "style-src 'self' 'unsafe-inline'",  # Tailwind precisa de unsafe-inline
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
        ]

        # Adicionar APIs externas permitidas
        if settings.deepseek_base_url:
            directives.append(f"connect-src 'self' {settings.deepseek_base_url}")
        if settings.openrouter_base_url:
            directives.append(f"connect-src 'self' {settings.openrouter_base_url}")

        # Frame ancestors
        directives.append("frame-ancestors 'self'")

        return "; ".join(directives)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Adiciona security headers à resposta."""
        response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # Apenas em produção e se HTTPS estiver configurado
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # X-Frame-Options - Previne clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # X-Content-Type-Options - Previne MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection - Ativa proteção XSS do navegador
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy - Controla informações enviadas no referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy - Controla features do navegador
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Content-Security-Policy
        # Em produção, usar política mais restritiva
        if settings.is_production:
            response.headers["Content-Security-Policy"] = self.csp_policy
        else:
            # Em desenvolvimento, política mais permissiva
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; "
                "frame-ancestors 'self'"
            )

        # X-Permitted-Cross-Domain-Policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Remove informações do servidor (se adicionadas por outros middlewares)
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response

