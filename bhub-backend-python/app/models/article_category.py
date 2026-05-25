"""
Tabela de associação many-to-many entre Article e Category.
Permite que um artigo tenha múltiplas categorias.
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, Table, UniqueConstraint

from app.database import Base

# Tabela de associação many-to-many entre Article e Category
article_categories = Table(
    "article_categories",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("confidence", Float, nullable=True),  # Confiança específica desta categoria para este artigo
    Column("is_primary", Boolean, default=False),  # Indica se é a categoria primária
    Column("auto_created", Boolean, default=False),  # Indica se a categoria foi criada automaticamente
    UniqueConstraint("article_id", "category_id", name="uq_article_category"),
)
