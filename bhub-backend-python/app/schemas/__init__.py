"""
Schemas Pydantic da aplicação BHUB.
"""

from app.schemas.article import (
    ArticleCreate,
    ArticleHighlightRequest,
    ArticleListResponse,
    ArticleResponse,
    ArticleSearchParams,
    ArticleSimilarResponse,
    ArticleUpdate,
    AuthorResponse,
    PDFUploadResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from app.schemas.banner import (
    BannerClickRequest,
    BannerCreate,
    BannerListResponse,
    BannerResponse,
    BannerUpdate,
)
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    CategoryWithStats,
)
from app.schemas.common import (
    ErrorResponse,
    HealthResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    StatsResponse,
)
from app.schemas.feed import (
    FeedCreate,
    FeedListResponse,
    FeedResponse,
    FeedSyncAllResult,
    FeedSyncResult,
    FeedTestResult,
    FeedUpdate,
)
from app.schemas.analytics import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    AnalyticsOverviewResponse,
    AnalyticsSessionResponse,
    ContentStatsResponse,
    EventsStatsResponse,
    TimeSeriesDataPoint,
    TopPageResponse,
    TrafficStatsResponse,
)
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Common
    "MessageResponse",
    "ErrorResponse",
    "HealthResponse",
    "StatsResponse",
    "PaginationParams",
    "PaginatedResponse",
    # User
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "TokenResponse",
    "LoginRequest",
    # Category
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
    "CategoryWithStats",
    # Feed
    "FeedCreate",
    "FeedUpdate",
    "FeedResponse",
    "FeedListResponse",
    "FeedTestResult",
    "FeedSyncResult",
    "FeedSyncAllResult",
    # Article
    "ArticleCreate",
    "ArticleUpdate",
    "ArticleResponse",
    "ArticleListResponse",
    "ArticleSearchParams",
    "ArticleSimilarResponse",
    "ArticleHighlightRequest",
    "AuthorResponse",
    "ScrapeRequest",
    "ScrapeResponse",
    "PDFUploadResponse",
    # Banner
    "BannerCreate",
    "BannerUpdate",
    "BannerResponse",
    "BannerListResponse",
    "BannerClickRequest",
    # Analytics
    "AnalyticsEventCreate",
    "AnalyticsEventResponse",
    "AnalyticsSessionResponse",
    "AnalyticsOverviewResponse",
    "TrafficStatsResponse",
    "ContentStatsResponse",
    "EventsStatsResponse",
    "TimeSeriesDataPoint",
    "TopPageResponse",
]
