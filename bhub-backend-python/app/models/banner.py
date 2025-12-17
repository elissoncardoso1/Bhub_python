"""
Modelo de banner publicitário.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BannerPosition(str, enum.Enum):
    """Posições disponíveis para banners."""

    HEADER = "HEADER"
    SIDEBAR = "SIDEBAR"
    BETWEEN_ARTICLES = "BETWEEN_ARTICLES"
    FOOTER = "FOOTER"


class Banner(BaseModel):
    """
    Banner publicitário ou informativo.
    """

    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Conteúdo
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Posição e prioridade
    position: Mapped[BannerPosition] = mapped_column(
        Enum(BannerPosition),
        default=BannerPosition.SIDEBAR,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status e datas
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Estatísticas
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    @property
    def is_visible(self) -> bool:
        """Verifica se o banner deve ser exibido."""
        if not self.is_active:
            return False

        now = datetime.utcnow()

        if self.start_date and now < self.start_date.replace(tzinfo=None):
            return False

        if self.end_date and now > self.end_date.replace(tzinfo=None):
            return False

        return True

    @property
    def ctr(self) -> float:
        """Calcula Click-Through Rate."""
        if self.view_count == 0:
            return 0.0
        return (self.click_count / self.view_count) * 100

    def __repr__(self) -> str:
        return f"Banner(id={self.id}, title={self.title}, position={self.position})"
