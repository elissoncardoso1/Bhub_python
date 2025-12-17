"""
Schemas de usuário.
"""

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import Field

from app.models.user import UserRole
from app.schemas.common import BaseSchema


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema de leitura de usuário."""

    name: str | None = None
    role: UserRole = UserRole.USER
    avatar_url: str | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class UserCreate(schemas.BaseUserCreate):
    """Schema de criação de usuário."""

    name: str | None = None
    role: UserRole = UserRole.USER


class UserUpdate(schemas.BaseUserUpdate):
    """Schema de atualização de usuário."""

    name: str | None = None
    role: UserRole | None = None
    avatar_url: str | None = None


class UserResponse(BaseSchema):
    """Resposta de usuário para API."""

    id: uuid.UUID
    email: str
    name: str | None
    role: UserRole
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseSchema):
    """Resposta de token JWT."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseSchema):
    """Request de login."""

    email: str = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=6, description="Senha do usuário")
