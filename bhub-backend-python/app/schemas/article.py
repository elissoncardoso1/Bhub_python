"""
Schemas de artigo.
"""

from datetime import datetime

from pydantic import Field, HttpUrl, computed_field

from app.models.article import SourceType
from app.schemas.category import CategoryResponse
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class AuthorResponse(BaseSchema):
    """Resposta de autor."""

    id: int
    name: str
    orcid: str | None = None
    affiliation: str | None = None
    role: str | None = "author"


class ArticleBase(BaseSchema):
    """Campos base de artigo."""

    title: str = Field(..., min_length=1, max_length=500)
    abstract: str | None = None
    keywords: str | None = None
    original_url: str | None = Field(default=None, max_length=500)
    pdf_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    publication_date: datetime | None = None
    journal_name: str | None = Field(default=None, max_length=255)
    volume: str | None = Field(default=None, max_length=50)
    issue: str | None = Field(default=None, max_length=50)
    pages: str | None = Field(default=None, max_length=50)
    doi: str | None = Field(default=None, max_length=100)
    language: str = "en"


class ArticleCreate(ArticleBase):
    """Schema de criação de artigo."""

    category_id: int | None = None
    feed_id: int | None = None
    authors: list[str] = []  # Lista de nomes de autores


class ArticleUpdate(BaseSchema):
    """Schema de atualização de artigo."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    abstract: str | None = None
    keywords: str | None = None
    original_url: str | None = None
    pdf_url: str | None = None
    image_url: str | None = None
    publication_date: datetime | None = None
    journal_name: str | None = None
    category_id: int | None = None
    highlighted: bool | None = None
    impact_score: float | None = Field(default=None, ge=1, le=10)
    is_published: bool | None = None


class ArticleResponse(ArticleBase, TimestampSchema):
    """Resposta de artigo."""

    id: int
    external_id: str | None = None
    title_translated: str | None = None
    abstract_translated: str | None = None
    category_id: int | None = None
    category: CategoryResponse | None = None
    impact_score: float
    classification_confidence: float | None = None
    highlighted: bool
    is_published: bool
    source_type: SourceType
    feed_id: int | None = None
    feed_name: str | None = None
    pdf_file_path: str | None = None
    pdf_file_size: int | None = None
    view_count: int
    download_count: int
    authors: list[AuthorResponse] = []
    has_pdf: bool = False
    has_pdf: bool = False

    @computed_field
    def source_category(self) -> str:
        """Categoria da fonte (computed)."""
        # Journals are PDF/MANUAL OR have a journal_name defined (even if RSS)
        if self.source_type in [SourceType.PDF, SourceType.MANUAL] or self.journal_name:
            return "journal"
        return "portal"


class ArticleListResponse(PaginatedResponse[ArticleResponse]):
    """Lista paginada de artigos."""

    pass


class ArticleSearchParams(BaseSchema):
    """Parâmetros de busca de artigos."""

    search: str | None = Field(default=None, min_length=2, max_length=200)
    category_id: int | None = None
    author: str | None = None
    feed_id: int | None = None
    highlighted: bool | None = None
    has_pdf: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_by: str = Field(default="publication_date", pattern=r"^(publication_date|title|impact_score|view_count|created_at)$")
    sort_order: str = Field(default="desc", pattern=r"^(asc|desc)$")


class ArticleSimilarResponse(BaseSchema):
    """Artigos similares."""

    articles: list[ArticleResponse]


class ArticleHighlightRequest(BaseSchema):
    """Request para destacar artigo."""

    highlighted: bool


class ScrapeRequest(BaseSchema):
    """Request para scraping de URL."""

    url: str = Field(..., max_length=500)
    category_id: int | None = None


class ScrapeResponse(BaseSchema):
    """Resposta de scraping."""

    success: bool
    article: ArticleResponse | None = None
    error: str | None = None


class PDFUploadResponse(BaseSchema):
    """Resposta de upload de PDF."""

    success: bool
    article_id: int | None = None
    message: str
    duplicate: bool = False
