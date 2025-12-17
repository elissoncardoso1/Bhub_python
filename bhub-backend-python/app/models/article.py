"""
Modelo de artigo científico.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.author import article_authors
from app.models.base import BaseModel


class SourceType(str, enum.Enum):
    """Tipo de fonte do artigo."""

    RSS = "RSS"
    SCRAPING = "SCRAPING"
    PDF = "PDF"
    MANUAL = "MANUAL"


class Article(BaseModel):
    """
    Artigo científico agregado.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identificação externa
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    doi: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)

    # Metadados principais
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_translated: Mapped[str | None] = mapped_column(String(500), nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract_translated: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # Separadas por vírgula
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # URLs
    original_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Publicação
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    journal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issue: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Classificação e scoring
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    impact_score: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)  # 1-10
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    highlighted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Fonte
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType),
        default=SourceType.RSS,
        nullable=False,
    )
    feed_id: Mapped[int | None] = mapped_column(ForeignKey("feeds.id"), nullable=True, index=True)

    # PDF específico
    pdf_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Estatísticas
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cache de tradução
    translation_cache: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Relacionamentos
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="articles",
        lazy="joined",
    )
    feed: Mapped["Feed"] = relationship(
        "Feed",
        back_populates="articles",
        lazy="joined",
    )
    authors: Mapped[list["Author"]] = relationship(
        "Author",
        secondary=article_authors,
        back_populates="articles",
        lazy="selectin",
    )
    pdf_metadata: Mapped["PDFMetadata | None"] = relationship(
        "PDFMetadata",
        back_populates="article",
        uselist=False,
        lazy="joined",
    )

    # Índices compostos
    __table_args__ = (
        Index("ix_articles_category_date", "category_id", "publication_date"),
        Index("ix_articles_highlighted_date", "highlighted", "publication_date"),
        Index("ix_articles_feed_date", "feed_id", "publication_date"),
    )

    @property
    def authors_str(self) -> str:
        """Retorna string com nomes dos autores."""
        if not self.authors:
            return ""
        return ", ".join(author.name for author in self.authors)

    @property
    def has_pdf(self) -> bool:
        """Verifica se artigo tem PDF local."""
        return bool(self.pdf_file_path)

    @property
    def feed_name(self) -> str | None:
        """Retorna nome do feed de origem."""
        return self.feed.name if self.feed else self.journal_name

    def __repr__(self) -> str:
        return f"Article(id={self.id}, title={self.title[:50]}...)"


# Import necessário para os relacionamentos funcionarem
from app.models.author import Author  # noqa: E402, F811
from app.models.category import Category  # noqa: E402, F811
from app.models.feed import Feed  # noqa: E402, F811
from app.models.pdf_metadata import PDFMetadata  # noqa: E402, F811
