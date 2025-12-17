"""
Schemas de feed.
"""

from datetime import datetime

from pydantic import Field, HttpUrl

from app.models.feed import FeedType, SyncFrequency
from app.schemas.common import BaseSchema, TimestampSchema


class FeedBase(BaseSchema):
    """Campos base de feed."""

    name: str = Field(..., min_length=1, max_length=255)
    journal_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    feed_url: str = Field(..., max_length=500)
    feed_type: FeedType = FeedType.RSS
    website_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    sync_frequency: SyncFrequency = SyncFrequency.HOURLY


class FeedCreate(FeedBase):
    """Schema de criação de feed."""

    pass


class FeedUpdate(BaseSchema):
    """Schema de atualização de feed."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    journal_name: str | None = None
    description: str | None = None
    feed_url: str | None = Field(default=None, max_length=500)
    website_url: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None
    sync_frequency: SyncFrequency | None = None


class FeedResponse(FeedBase, TimestampSchema):
    """Resposta de feed."""

    id: int
    last_sync_at: datetime | None
    last_successful_sync_at: datetime | None
    error_count: int
    last_error: str | None
    total_articles: int
    articles_last_sync: int


class FeedListResponse(BaseSchema):
    """Lista de feeds."""

    feeds: list[FeedResponse]
    total: int


class FeedTestResult(BaseSchema):
    """Resultado de teste de feed."""

    success: bool
    feed_title: str | None = None
    feed_description: str | None = None
    items_count: int = 0
    sample_items: list[dict] = []
    error: str | None = None


class FeedSyncResult(BaseSchema):
    """Resultado de sincronização de feed."""

    feed_id: int
    feed_name: str
    success: bool
    new_articles: int = 0
    updated_articles: int = 0
    errors: list[str] = []
    duration_seconds: float = 0.0


class FeedSyncAllResult(BaseSchema):
    """Resultado de sincronização de todos os feeds."""

    total_feeds: int
    successful: int
    failed: int
    new_articles: int
    results: list[FeedSyncResult]
    duration_seconds: float
