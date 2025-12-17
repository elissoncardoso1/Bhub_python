"""
Schemas de banner.
"""

from datetime import datetime

from pydantic import Field

from app.models.banner import BannerPosition
from app.schemas.common import BaseSchema, TimestampSchema


class BannerBase(BaseSchema):
    """Campos base de banner."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    image_url: str = Field(..., max_length=500)
    link_url: str | None = Field(default=None, max_length=500)
    alt_text: str | None = Field(default=None, max_length=255)
    position: BannerPosition = BannerPosition.SIDEBAR
    priority: int = Field(default=0, ge=0)
    is_active: bool = True
    start_date: datetime | None = None
    end_date: datetime | None = None


class BannerCreate(BannerBase):
    """Schema de criação de banner."""

    pass


class BannerUpdate(BaseSchema):
    """Schema de atualização de banner."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    link_url: str | None = None
    alt_text: str | None = None
    position: BannerPosition | None = None
    priority: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class BannerResponse(BannerBase, TimestampSchema):
    """Resposta de banner."""

    id: int
    view_count: int
    click_count: int
    ctr: float


class BannerListResponse(BaseSchema):
    """Lista de banners."""

    banners: list[BannerResponse]


class BannerClickRequest(BaseSchema):
    """Request de clique em banner."""

    banner_id: int
