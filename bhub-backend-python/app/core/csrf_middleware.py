"""
Middleware para gerenciar tokens CSRF automaticamente.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.csrf import csrf_protection
from app.core.logging import log


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware que gerencia tokens CSRF automaticamente.
    - Gera e define token CSRF em cookies para requisições GET
    - Valida tokens CSRF em requisições mutáveis (se configurado)
    """

    def __init__(self, app: ASGIApp, auto_validate: bool = False):
        """
        Args:
            app: Aplicação ASGI
            auto_validate: Se True, valida automaticamente em todas as rotas mutáveis.
                          Se False, validação deve ser feita manualmente via dependência.
        """
        super().__init__(app)
        self.auto_validate = auto_validate

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processa requisição e gerencia CSRF."""
        # Rotas que não precisam de CSRF
        excluded_paths = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",  # Login usa outro método
            "/api/v1/auth/refresh",  # Refresh token usa outro método
        }
        
        path = request.url.path
        if any(path.startswith(excluded) for excluded in excluded_paths):
            return await call_next(request)

        # Para requisições GET/HEAD, gerar ou manter token CSRF
        if request.method in ("GET", "HEAD"):
            response = await call_next(request)
            
            # Se não há token CSRF no cookie, gerar um novo
            if not csrf_protection.get_token_from_cookie(request):
                token = csrf_protection.generate_token()
                csrf_protection.set_csrf_cookie(response, token)
            
            return response

        # Para requisições mutáveis, validar CSRF se auto_validate estiver ativo
        if self.auto_validate and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                csrf_protection.validate_csrf(request, require_token=True)
            except Exception as e:
                # Se validação falhar, retornar erro
                from fastapi import HTTPException, status
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token CSRF inválido ou ausente",
                )

        return await call_next(request)

