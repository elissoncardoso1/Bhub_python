"""
Modelo de usuário para autenticação.
"""

import enum
from datetime import datetime

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    """Roles de usuário disponíveis."""

    USER = "USER"
    ADMIN = "ADMIN"


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    Modelo de usuário.
    Herda de SQLAlchemyBaseUserTableUUID do fastapi-users que inclui:
    - id (UUID)
    - email
    - hashed_password
    - is_active
    - is_superuser
    - is_verified
    """

    __tablename__ = "users"

    # Campos adicionais
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @property
    def is_admin(self) -> bool:
        """Verifica se o usuário é admin."""
        return self.role == UserRole.ADMIN or self.is_superuser

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, role={self.role})"
