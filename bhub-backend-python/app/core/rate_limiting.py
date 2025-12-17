"""
Helpers para rate limiting nas rotas da API.
"""

from functools import wraps
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.main import limiter


def rate_limit(limit: str, key_func: Callable = None):
    """
    Decorator para aplicar rate limiting em rotas.
    
    Args:
        limit: String no formato "X/minute", "Y/hour", etc.
        key_func: Função para obter a chave de rate limiting (default: IP)
    
    Exemplos:
        @rate_limit("100/minute")  # 100 requisições por minuto
        @rate_limit("10/minute", key_func=lambda r: r.user.id)  # Por usuário
    """
    if key_func is None:
        key_func = get_remote_address
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Encontrar Request nos argumentos
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                # Aplicar rate limit
                limiter.limit(limit, key_func=key_func)(func)(*args, **kwargs)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_user_id_for_rate_limit(request: Request) -> str:
    """
    Obtém ID do usuário para rate limiting baseado em token JWT.
    Retorna IP se usuário não estiver autenticado.
    """
    # Tentar obter token do header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Tentar decodificar JWT para obter user_id
        # Usamos apenas para rate limiting, então não validamos completamente
        try:
            from jose import jwt
            from app.config import settings
            # Decodificar sem verificar expiração (apenas para rate limiting)
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                options={"verify_exp": False, "verify_signature": True}
            )
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            # Se falhar, usar IP
            pass
    
    # Fallback para IP
    return get_remote_address(request)

