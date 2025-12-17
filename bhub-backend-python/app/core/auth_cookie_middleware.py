"""
Middleware para adicionar cookies HttpOnly em respostas de autenticação.
Adiciona cookies seguros mantendo compatibilidade com Bearer tokens.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings


class AuthCookieMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona cookies HttpOnly em respostas de login.
    Mantém compatibilidade com Bearer tokens no header.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.cookie_name = "access_token"
        self.cookie_secure = settings.is_production  # Apenas HTTPS em produção
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processa requisição e adiciona cookies em respostas de login."""
        response = await call_next(request)
        
        # Verificar se é uma resposta de login bem-sucedida
        if (
            request.url.path == "/api/v1/auth/login" 
            and request.method == "POST"
            and response.status_code == 200
        ):
            # Tentar extrair token do body da resposta
            try:
                import json
                # Ler body uma vez
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk
                
                # Parse do JSON
                data = json.loads(body_bytes.decode())
                token = data.get("access_token")
                
                if token:
                    # Criar nova resposta com cookie
                    from starlette.responses import JSONResponse
                    new_response = JSONResponse(
                        content=data,
                        status_code=response.status_code,
                    )
                    # Adicionar cookie HttpOnly
                    new_response.set_cookie(
                        key=self.cookie_name,
                        value=token,
                        max_age=settings.access_token_expire_minutes * 60,
                        httponly=True,
                        secure=self.cookie_secure,
                        samesite="strict",
                        path="/",
                    )
                    return new_response
            except Exception:
                # Se falhar, retornar resposta original
                pass
        
        # Remover cookie em logout
        if (
            request.url.path == "/api/v1/auth/logout"
            and request.method == "POST"
        ):
            response.delete_cookie(
                key=self.cookie_name,
                httponly=True,
                secure=self.cookie_secure,
                samesite="strict",
                path="/",
            )
        
        return response

