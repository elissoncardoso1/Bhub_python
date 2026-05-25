"""
Middleware para compatibilidade: transformar cookie `access_token` em header Authorization.

Permite que o frontend SSR/HTMX use HttpOnly cookies sem precisar gerenciar JWT no JS,
mantendo compatibilidade com o BearerTransport do fastapi-users.
"""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class AccessTokenCookieMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, cookie_name: str = "access_token"):
        super().__init__(app)
        self.cookie_name = cookie_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not request.headers.get("authorization"):
            token = request.cookies.get(self.cookie_name)
            if token:
                headers = list(request.scope.get("headers") or [])
                headers.append((b"authorization", f"Bearer {token}".encode()))
                request.scope["headers"] = headers

        return await call_next(request)
