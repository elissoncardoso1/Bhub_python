"""
Sistema de segurança e autenticação.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import log
from app.database import get_async_session
from app.models.user import User, UserRole


# Database adapter
async def get_user_db(session: Annotated[AsyncSession, Depends(get_async_session)]):
    yield SQLAlchemyUserDatabase(session, User)


# User Manager
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Gerenciador de usuários."""

    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def on_after_register(self, user: User, request=None):
        from app.core.log_sanitizer import sanitize_log_message
        log.info(sanitize_log_message(f"Usuário registrado: {user.email}"))

    async def on_after_login(self, user: User, request=None, response=None):
        from app.core.log_sanitizer import sanitize_log_message
        log.info(sanitize_log_message(f"Login realizado: {user.email}"))
        # Atualizar último login
        user.last_login_at = datetime.utcnow()

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        from app.core.log_sanitizer import sanitize_log_message
        # Não logar o token de reset
        log.info(sanitize_log_message(f"Solicitação de reset de senha: {user.email}"))

    async def on_after_reset_password(self, user: User, request=None):
        from app.core.log_sanitizer import sanitize_log_message
        log.info(sanitize_log_message(f"Senha resetada: {user.email}"))


async def get_user_manager(user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)]):
    yield UserManager(user_db)


# JWT Strategy
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.access_token_expire_minutes * 60,
        algorithm=settings.algorithm,
    )


# Bearer Transport (compatível com frontend atual)
# Cookies HttpOnly são adicionados via middleware (AuthCookieMiddleware)
auth_transport = BearerTransport(tokenUrl="/api/v1/auth/login")

# Authentication Backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=auth_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Dependencies para uso nas rotas
current_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)


async def current_admin_user(
    user: Annotated[User, Depends(current_user)],
) -> User:
    """Verifica se o usuário é admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Requer permissão de administrador.",
        )
    return user


# Type aliases para uso nas rotas
CurrentUser = Annotated[User, Depends(current_user)]
CurrentAdmin = Annotated[User, Depends(current_admin_user)]
CurrentSuperuser = Annotated[User, Depends(current_superuser)]
