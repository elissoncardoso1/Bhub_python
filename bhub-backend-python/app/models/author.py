"""
Modelo de autor e relacionamento com artigos.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel

# Tabela de associação many-to-many entre Article e Author
article_authors = Table(
    "article_authors",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
    Column("position", Integer, default=0),  # Ordem do autor no artigo
    Column("role", String(50), default="author"),  # Papel: author, editor, etc.
    UniqueConstraint("article_id", "author_id", name="uq_article_author"),
)


class Author(BaseModel):
    """
    Autor normalizado.
    Mantém nomes de autores únicos para evitar duplicação.
    """

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Nome completo normalizado
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Nome normalizado para busca (sem acentos, lowercase)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Informações adicionais (quando disponíveis)
    orcid: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    affiliation: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Estatísticas
    article_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relacionamentos
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        secondary=article_authors,
        back_populates="authors",
        lazy="selectin",
    )

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normaliza nome do autor para comparação.
        Remove acentos, converte para lowercase, remove caracteres especiais.
        """
        import re
        import unicodedata

        # Remove acentos
        normalized = unicodedata.normalize("NFKD", name)
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))

        # Lowercase e remove caracteres especiais
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

        # Remove espaços extras
        normalized = " ".join(normalized.split())

        return normalized

    def __repr__(self) -> str:
        return f"Author(id={self.id}, name={self.name})"
