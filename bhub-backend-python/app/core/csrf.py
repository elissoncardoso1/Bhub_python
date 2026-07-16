"""
Sistema de proteção CSRF (Cross-Site Request Forgery).
"""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

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

    def get_token_from_cookie(self, request: Request) -> str | None:
        """Obtém o token CSRF do cookie."""
        return request.cookies.get(self.cookie_name)

    def get_token_from_header(self, request: Request) -> str | None:
        """Obtém o token CSRF do header."""
        return request.headers.get(self.header_name.lower())

    def validate_csrf(
        self,
        request: Request,
        require_token: bool = True,
        fallback_token: str | None = None,
    ) -> bool:
        """
        Valida o token CSRF.

        Args:
            request: Requisição FastAPI
            require_token: Se True, exige token. Se False, apenas valida se presente.
            fallback_token: Token vindo de um campo de formulário HTML
                (double-submit), usado quando o header não está presente —
                cobre forms HTML puros sem JS que não conseguem setar o header.

        Returns:
            True se válido ou se não requerido

        Raises:
            HTTPException: Se token inválido ou ausente quando requerido
        """
        # Métodos seguros não precisam de CSRF
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        # Obter token do header (ou fallback vindo de campo de formulário)
        header_token = self.get_token_from_header(request) or fallback_token

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

        # Se requer token mas não está no header nem no campo de formulário
        if require_token and not header_token:
            log.warning(f"CSRF: Token ausente no header para {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Token CSRF requerido. Envie no header '{self.header_name}' "
                    "ou no campo 'csrf_token' do formulário."
                ),
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
        # Caso a middleware já tenha gerado um token para esta request (GET/HEAD),
        # reutilizar para manter consistência entre meta tag e cookie.
        token = getattr(request.state, "csrf_token", None) or csrf_protection.generate_token()
        request.state.csrf_token = token
    return token


async def validate_csrf_token(
    request: Request,
    require_token: bool = True,
) -> bool:
    """
    Dependência para validar token CSRF em rotas mutáveis.

    Valida via header X-CSRF-Token ou, em requisições de formulário HTML
    (sem JS para setar o header), via campo `csrf_token` do próprio form.

    Usage:
        @router.post("/endpoint")
        async def my_endpoint(
            request: Request,
            csrf_valid: Annotated[bool, Depends(validate_csrf_token)]
        ):
            ...
    """
    fallback: str | None = None
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        content_type = request.headers.get("content-type", "")
        if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            form = await request.form()  # Starlette cacheia; Form(...) das rotas segue funcionando
            value = form.get("csrf_token")
            fallback = value if isinstance(value, str) else None
    return csrf_protection.validate_csrf(request, require_token=require_token, fallback_token=fallback)


# Variante permissiva: valida apenas se houver cookie CSRF
async def validate_csrf_if_present(request: Request) -> bool:
    return csrf_protection.validate_csrf(request, require_token=False)


# Type alias para uso nas rotas
CSRFValid = Annotated[bool, Depends(validate_csrf_token)]
CSRFOptional = Annotated[bool, Depends(validate_csrf_if_present)]
