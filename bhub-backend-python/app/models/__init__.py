"""
Modelos SQLAlchemy da aplicação BHUB.
"""

from app.models.article import Article, SourceType
from app.models.author import Author, article_authors
from app.models.banner import Banner, BannerPosition
from app.models.base import BaseModel, TimestampMixin
from app.models.category import DEFAULT_CATEGORIES, Category
from app.models.contact import ContactMessage, MessageStatus
from app.models.feed import (
    PDF_FEED_NAME,
    PDF_FEED_URL,
    SCRAPING_FEED_NAME,
    SCRAPING_FEED_URL,
    Feed,
    FeedType,
    SyncFrequency,
)
from app.models.pdf_metadata import PDFMetadata, ProcessingStatus
from app.models.translation_cache import TranslationCache
from app.models.user import User, UserRole
from app.models.analytics import (
    AnalyticsEvent,
    AnalyticsMetric,
    AnalyticsSession,
    EventType,
    SessionStatus,
)

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    # User
    "User",
    "UserRole",
    # Category
    "Category",
    "DEFAULT_CATEGORIES",
    # Feed
    "Feed",
    "FeedType",
    "SyncFrequency",
    "PDF_FEED_URL",
    "PDF_FEED_NAME",
    "SCRAPING_FEED_URL",
    "SCRAPING_FEED_NAME",
    # Author
    "Author",
    "article_authors",
    # Article
    "Article",
    "SourceType",
    # PDF
    "PDFMetadata",
    "ProcessingStatus",
    # Banner
    "Banner",
    "BannerPosition",
    # Contact
    "ContactMessage",
    "MessageStatus",
    # Translation Cache
    "TranslationCache",
    # Analytics
    "AnalyticsEvent",
    "AnalyticsSession",
    "AnalyticsMetric",
    "EventType",
    "SessionStatus",
]
