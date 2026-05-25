"""
Modelo para locks distribuídos do scheduler.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SchedulerLock(BaseModel):
    """
    Lock distribuído para prevenir execução duplicada de jobs.
    Usa o banco de dados como fonte de verdade.
    """

    __tablename__ = "scheduler_locks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Nome do lock (ex: "sync_feeds", "cleanup_logs")
    lock_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # ID do processo/instância que possui o lock
    instance_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timestamp de quando o lock foi adquirido
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Timestamp de quando o lock expira (TTL)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Última atualização (heartbeat)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"SchedulerLock(lock_name={self.lock_name}, instance_id={self.instance_id}, expires_at={self.expires_at})"
