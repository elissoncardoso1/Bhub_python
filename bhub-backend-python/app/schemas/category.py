"""
Schemas de categoria.
"""

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class CategoryBase(BaseSchema):
    """Campos base de categoria."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    keywords: str | None = None


class CategoryCreate(CategoryBase):
    """Schema de criação de categoria."""

    pass


class CategoryUpdate(BaseSchema):
    """Schema de atualização de categoria."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    keywords: str | None = None


class CategoryResponse(CategoryBase, TimestampSchema):
    """Resposta de categoria."""

    id: int
    article_count: int = 0


class CategoryListResponse(BaseSchema):
    """Lista de categorias."""

    categories: list[CategoryResponse]


class CategoryWithStats(CategoryResponse):
    """Categoria com estatísticas."""

    articles_this_month: int = 0
    articles_this_week: int = 0
