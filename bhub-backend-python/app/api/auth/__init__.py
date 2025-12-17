"""
Rotas de autenticação.
"""

from fastapi import APIRouter

from app.core.security import auth_backend, fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# Rotas de login/logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
)

# Rotas de registro
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

# Rotas de reset de senha
router.include_router(
    fastapi_users.get_reset_password_router(),
)

# Rotas de verificação
router.include_router(
    fastapi_users.get_verify_router(UserRead),
)

# Rotas de gerenciamento de usuário
users_router = APIRouter(prefix="/api/v1/users", tags=["Users"])
users_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)

__all__ = ["router", "users_router"]
