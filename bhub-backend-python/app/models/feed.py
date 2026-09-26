"""
Modelo de feed (fonte de artigos).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article

# Feeds desativados por erro voltam a ser sondados após este intervalo
RECOVERY_PROBE_INTERVAL_DAYS = 7


class FeedType(enum.StrEnum):
    """Tipo de feed."""

    RSS = "RSS"
    ATOM = "ATOM"
    SCRAPING = "SCRAPING"
    PDF = "PDF"
    INTERNAL = "INTERNAL"


class SyncFrequency(enum.StrEnum):
    """Frequência de sincronização."""

    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MANUAL = "MANUAL"


class FeedJournalSource(enum.StrEnum):
    """Via de ingestão de um periódico científico.

    ``RSS`` é o caminho histórico (feed RSS/Atom da editora). ``CROSSREF``
    troca a fonte pela API REST do Crossref, indexada por ISSN — usada quando
    a editora serve o endpoint de RSS atrás de anti-bot (ver ADR-0007).
    """

    RSS = "RSS"
    CROSSREF = "CROSSREF"


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

    # Periódicos científicos: via de ingestão e ISSN de consulta (ADR-0007).
    # ``journal_source`` roteia o sync; ``issn`` é a chave no Crossref.
    journal_source: Mapped[FeedJournalSource] = mapped_column(
        Enum(FeedJournalSource),
        default=FeedJournalSource.RSS,
        nullable=False,
    )
    issn: Mapped[str | None] = mapped_column(String(12), nullable=True)

    # Status e sincronização
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    # Marca que a desativação foi feita automaticamente por excesso de erro, e
    # não por curadoria. É o que permite a sondagem de recuperação devolver o
    # feed à rotação sem jamais reativar algo que um humano desligou de propósito.
    deactivated_by_errors: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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

    # Cache HTTP (conditional GET)
    http_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    http_last_modified: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Estatísticas
    total_articles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    articles_last_sync: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Configurações específicas
    custom_headers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    scraping_selectors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Relacionamentos
    articles: Mapped[list[Article]] = relationship(
        "Article",
        back_populates="feed",
        lazy="selectin",
    )

    @property
    def is_internal(self) -> bool:
        """Verifica se é um feed interno (para scraping/PDF)."""
        return self.feed_url.startswith("internal://")

    @property
    def exhausted_errors(self) -> bool:
        """True quando o feed atingiu ``max_errors`` e deve sair da rotação normal."""
        return self.error_count >= self.max_errors

    def _recovery_probe_due(self) -> bool:
        """True se já passou tempo suficiente para sondar um feed com erro."""
        from datetime import timedelta

        if self.last_sync_at is None:
            return True
        probe_interval = timedelta(days=RECOVERY_PROBE_INTERVAL_DAYS)
        return datetime.utcnow() - self.last_sync_at.replace(tzinfo=None) > probe_interval

    @property
    def needs_sync(self) -> bool:
        """Verifica se o feed precisa ser sincronizado.

        Feeds marcados por excesso de erro **não** são morte permanente: saem da
        rotação normal e voltam a ser sondados a cada
        ``RECOVERY_PROBE_INTERVAL_DAYS``. Se a sonda tiver sucesso, o feed é
        reativado automaticamente — o ``error_count`` zerado pelo sync limpa o
        estado de erro.

        A reativação automática só vale para desativação **causada por erro**
        (``deactivated_by_errors``): desativar um feed pela curadoria é
        definitivo, e nenhum código reativa o que um humano desligou.
        """
        from datetime import timedelta

        if self.is_internal:
            return False

        if self.is_active:
            if self.exhausted_errors:
                # Já passou do limite mas continua ativo (ex.: `max_errors`
                # aumentado depois de o feed acumular erros). Sonda em vez de
                # seguir numa rotação que só produz falhas.
                return self._recovery_probe_due()

            if self.last_sync_at is None:
                return True

            now = datetime.utcnow()
            intervals = {
                SyncFrequency.HOURLY: timedelta(hours=1),
                SyncFrequency.DAILY: timedelta(days=1),
                SyncFrequency.WEEKLY: timedelta(weeks=1),
                SyncFrequency.MANUAL: timedelta(days=365),  # Praticamente nunca
            }
            interval = intervals.get(self.sync_frequency, timedelta(hours=1))
            return now - self.last_sync_at.replace(tzinfo=None) > interval

        # Inativo: só volta se foi desativado automaticamente por erro.
        if self.deactivated_by_errors:
            return self._recovery_probe_due()

        return False

    def __repr__(self) -> str:
        return f"Feed(id={self.id}, name={self.name}, type={self.feed_type})"


# Feed especial para PDFs
PDF_FEED_URL = "internal://pdf-uploads"
PDF_FEED_NAME = "PDF Uploads"

# Feed especial para Web Scraping
SCRAPING_FEED_URL = "internal://web-scraping"
SCRAPING_FEED_NAME = "Web Scraping"
