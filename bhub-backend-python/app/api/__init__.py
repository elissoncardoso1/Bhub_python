"""
Módulo de rotas da API.
"""

from app.api.auth import router as auth_router
from app.api.auth import users_router
from app.api.v1 import router as v1_router

__all__ = ["v1_router", "auth_router", "users_router"]
