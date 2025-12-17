"""
Sistema de proteção CSRF (Cross-Site Request Forgery).
"""

import secrets
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.core.logging import log


class CSRFProtection:
    """Gerenciador de proteção CSRF."""

    def __init__(self):
        self.token_length = 32
        self.header_name = "X-CSRF-Token"
        self.cookie_name = "csrf_token"

    def generate_token(self) -> str:
        """Gera um token CSRF seguro."""
        return secrets.token_urlsafe(self.token_length)

    def set_csrf_cookie(self, response: Response, token: str) -> None:
        """Define o token CSRF em um cookie HttpOnly."""
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            httponly=True,
            secure=not settings.is_development,  # Secure apenas em produção
            samesite="strict",
            max_age=3600 * 24,  # 24 horas
            path="/",
        )

    def get_token_from_cookie(self, request: Request) -> Optional[str]:
        """Obtém o token CSRF do cookie."""
        return request.cookies.get(self.cookie_name)

    def get_token_from_header(self, request: Request) -> Optional[str]:
        """Obtém o token CSRF do header."""
        return request.headers.get(self.header_name.lower())

    def validate_csrf(
        self,
        request: Request,
        require_token: bool = True,
    ) -> bool:
        """
        Valida o token CSRF.
        
        Args:
            request: Requisição FastAPI
            require_token: Se True, exige token. Se False, apenas valida se presente.
        
        Returns:
            True se válido ou se não requerido
        
        Raises:
            HTTPException: Se token inválido ou ausente quando requerido
        """
        # Métodos seguros não precisam de CSRF
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        # Obter token do header
        header_token = self.get_token_from_header(request)
        
        # Obter token do cookie
        cookie_token = self.get_token_from_cookie(request)

        # Se não há token no cookie, não há sessão CSRF válida
        if not cookie_token:
            if require_token:
                log.warning(f"CSRF: Token ausente no cookie para {request.method} {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token CSRF ausente. Faça login novamente.",
                )
            return True  # Não requerido, permitir

        # Se requer token mas não está no header
        if require_token and not header_token:
            log.warning(f"CSRF: Token ausente no header para {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token CSRF requerido. Envie no header '{self.header_name}'.",
            )

        # Validar se tokens coincidem
        if header_token and header_token != cookie_token:
            log.warning(f"CSRF: Token inválido para {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token CSRF inválido.",
            )

        return True


# Instância global
csrf_protection = CSRFProtection()


async def get_csrf_token(request: Request) -> str:
    """
    Dependência para obter token CSRF do cookie.
    Se não existir, gera um novo.
    """
    token = csrf_protection.get_token_from_cookie(request)
    if not token:
        token = csrf_protection.generate_token()
    return token


async def validate_csrf_token(
    request: Request,
    require_token: bool = True,
) -> bool:
    """
    Dependência para validar token CSRF em rotas mutáveis.
    
    Usage:
        @router.post("/endpoint")
        async def my_endpoint(
            request: Request,
            csrf_valid: Annotated[bool, Depends(validate_csrf_token)]
        ):
            ...
    """
    return csrf_protection.validate_csrf(request, require_token=require_token)


# Type alias para uso nas rotas
CSRFValid = Annotated[bool, Depends(validate_csrf_token)]

