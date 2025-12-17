"""
Modelo de metadados específicos de PDF.
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProcessingStatus(str, enum.Enum):
    """Status de processamento do PDF."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PDFMetadata(BaseModel):
    """
    Metadados específicos de arquivos PDF.
    """

    __tablename__ = "pdf_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Relacionamento com artigo
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Informações do arquivo
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # SHA-256
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")

    # Metadados extraídos
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Texto extraído
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Thumbnail
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Metadados do PDF (JSON)
    pdf_info: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON com info do PDF

    # Status de processamento
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamentos
    article: Mapped["Article"] = relationship(
        "Article",
        back_populates="pdf_metadata",
    )

    def __repr__(self) -> str:
        return f"PDFMetadata(id={self.id}, article_id={self.article_id}, status={self.processing_status})"


# Import para relacionamento
from app.models.article import Article  # noqa: E402, F811
