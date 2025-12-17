"""
Modelo de feed (fonte de artigos).
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class FeedType(str, enum.Enum):
    """Tipo de feed."""

    RSS = "RSS"
    ATOM = "ATOM"
    SCRAPING = "SCRAPING"
    PDF = "PDF"
    INTERNAL = "INTERNAL"


class SyncFrequency(str, enum.Enum):
    """Frequência de sincronização."""

    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MANUAL = "MANUAL"


class Feed(BaseModel):
    """
    Fonte de artigos.
    Pode ser um feed RSS/Atom, URL para scraping, ou fonte de PDFs.
    """

    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Informações básicas
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    journal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # URL e tipo
    feed_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    feed_type: Mapped[FeedType] = mapped_column(
        Enum(FeedType),
        default=FeedType.RSS,
        nullable=False,
    )
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status e sincronização
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    sync_frequency: Mapped[SyncFrequency] = mapped_column(
        Enum(SyncFrequency),
        default=SyncFrequency.HOURLY,
        nullable=False,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Contadores de erro
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_errors: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Estatísticas
    total_articles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    articles_last_sync: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Configurações específicas
    custom_headers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    scraping_selectors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Relacionamentos
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="feed",
        lazy="selectin",
    )

    @property
    def is_internal(self) -> bool:
        """Verifica se é um feed interno (para scraping/PDF)."""
        return self.feed_url.startswith("internal://")

    @property
    def needs_sync(self) -> bool:
        """Verifica se o feed precisa ser sincronizado."""
        if not self.is_active or self.is_internal:
            return False

        if self.error_count >= self.max_errors:
            return False

        if self.last_sync_at is None:
            return True

        from datetime import timedelta

        now = datetime.utcnow()
        intervals = {
            SyncFrequency.HOURLY: timedelta(hours=1),
            SyncFrequency.DAILY: timedelta(days=1),
            SyncFrequency.WEEKLY: timedelta(weeks=1),
            SyncFrequency.MANUAL: timedelta(days=365),  # Praticamente nunca
        }

        interval = intervals.get(self.sync_frequency, timedelta(hours=1))
        return now - self.last_sync_at.replace(tzinfo=None) > interval

    def __repr__(self) -> str:
        return f"Feed(id={self.id}, name={self.name}, type={self.feed_type})"


# Feed especial para PDFs
PDF_FEED_URL = "internal://pdf-uploads"
PDF_FEED_NAME = "PDF Uploads"

# Feed especial para Web Scraping
SCRAPING_FEED_URL = "internal://web-scraping"
SCRAPING_FEED_NAME = "Web Scraping"
