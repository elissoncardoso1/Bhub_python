"""
Rotas para gerenciamento de tokens CSRF.
"""

from fastapi import APIRouter, Request, Response

from app.core.csrf import csrf_protection, get_csrf_token
from app.core.logging import log

router = APIRouter(prefix="/csrf", tags=["CSRF"])


@router.get("/token")
async def get_csrf_token_endpoint(
    request: Request,
    response: Response,
):
    """
    Retorna o token CSRF atual ou gera um novo.
    O token também é definido em um cookie HttpOnly.
    """
    # Obter ou gerar token
    token = await get_csrf_token(request)
    
    # Se não havia token no cookie, definir agora
    if not csrf_protection.get_token_from_cookie(request):
        csrf_protection.set_csrf_cookie(response, token)
    
    return {
        "csrf_token": token,
        "header_name": csrf_protection.header_name,
    }

