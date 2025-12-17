"""
Schemas comuns e utilitários.
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Schema base com configurações comuns."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema com timestamps."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Parâmetros de paginação."""

    page: int = Field(default=1, ge=1, description="Número da página")
    page_size: int = Field(default=20, ge=1, le=100, description="Itens por página")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema, Generic[T]):
    """Resposta paginada genérica."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class MessageResponse(BaseSchema):
    """Resposta simples com mensagem."""

    message: str
    success: bool = True


class ErrorResponse(BaseSchema):
    """Resposta de erro."""

    detail: str
    code: str | None = None


class HealthResponse(BaseSchema):
    """Resposta de health check."""

    status: str = "healthy"
    version: str
    database: str = "connected"
    ml_model: str = "not_loaded"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatsResponse(BaseSchema):
    """Estatísticas gerais."""

    total_articles: int
    total_feeds: int
    total_categories: int
    total_authors: int
    total_pdfs: int
    articles_this_month: int
    articles_this_week: int
    highlighted_articles: int
    views_total: int
    downloads_total: int
