"""
Transport customizado para autenticação usando HttpOnly cookies.
"""

from typing import Optional

from fastapi import Response
from fastapi_users.authentication import AuthenticationBackend, BearerTransport
from fastapi_users.authentication.transport.base import TransportLogoutNotSupportedError


class CookieTransport(BearerTransport):
    """
    Transport que usa cookies HttpOnly para tokens JWT.
    Mais seguro que Bearer tokens no header Authorization.
    """
    
    def __init__(
        self,
        cookie_name: str = "access_token",
        cookie_max_age: int = 3600,  # 1 hora
        cookie_httponly: bool = True,
        cookie_secure: bool = True,  # Apenas HTTPS em produção
        cookie_samesite: str = "strict",
    ):
        self.cookie_name = cookie_name
        self.cookie_max_age = cookie_max_age
        self.cookie_httponly = cookie_httponly
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        # Manter compatibilidade com BearerTransport para tokenUrl
        super().__init__(tokenUrl="/api/v1/auth/login")
    
    async def login(self, token: str, response: Response) -> None:
        """Define o token em um cookie HttpOnly."""
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            max_age=self.cookie_max_age,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            path="/",
        )
        # Também retornar no body para compatibilidade com frontend atual
        # TODO: Remover isso após migração completa do frontend
        response.body = f'{{"access_token": "{token}", "token_type": "bearer"}}'.encode()
        response.headers["Content-Type"] = "application/json"
    
    async def logout(self, response: Response) -> None:
        """Remove o cookie de autenticação."""
        response.delete_cookie(
            key=self.cookie_name,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            path="/",
        )
    
    def get_token_from_request(self, request) -> Optional[str]:
        """Obtém o token do cookie ou do header Authorization (compatibilidade)."""
        # Primeiro tentar obter do cookie
        token = request.cookies.get(self.cookie_name)
        if token:
            return token
        
        # Fallback para header Authorization (compatibilidade)
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.split(" ")[1]
        
        return None

