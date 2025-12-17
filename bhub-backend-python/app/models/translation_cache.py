"""
Modelo para cache de traduções.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TranslationCache(BaseModel):
    """Cache de traduções para evitar chamadas repetidas à API."""
    
    __tablename__ = "translations_cache"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    
    content_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Hash SHA256 do texto normalizado + idiomas + modelo",
    )
    
    source_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Idioma de origem (ex: 'en', 'pt')",
    )
    
    target_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Idioma de destino (ex: 'pt-BR', 'en')",
    )
    
    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Texto original antes da tradução",
    )
    
    translated_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Texto traduzido",
    )
    
    model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="deepseek-chat",
        comment="Modelo/versão usado para tradução",
    )
    
    provider: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Provedor de IA usado (deepseek, openrouter, etc)",
    )
    
    last_accessed_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="Última vez que esta tradução foi acessada",
    )
    
    # Índices adicionais
    __table_args__ = (
        Index("idx_content_hash", "content_hash"),
        Index("idx_last_accessed", "last_accessed_at"),
        Index("idx_source_target", "source_language", "target_language"),
    )
    
    def __repr__(self) -> str:
        return (
            f"TranslationCache(id={self.id}, "
            f"source={self.source_language}, "
            f"target={self.target_language}, "
            f"hash={self.content_hash[:8]}...)"
        )

