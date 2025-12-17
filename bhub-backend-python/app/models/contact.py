"""
Modelo de mensagem de contato.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MessageStatus(str, enum.Enum):
    """Status da mensagem."""

    UNREAD = "UNREAD"
    READ = "READ"
    REPLIED = "REPLIED"
    ARCHIVED = "ARCHIVED"


class ContactMessage(BaseModel):
    """
    Mensagem de contato enviada pelo site.
    """

    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Informações do remetente
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Mensagem
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus),
        default=MessageStatus.UNREAD,
        nullable=False,
        index=True,
    )

    # Resposta (se houver)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"ContactMessage(id={self.id}, email={self.email}, status={self.status})"
