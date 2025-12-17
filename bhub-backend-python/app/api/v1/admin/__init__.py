"""
Rotas administrativas.
"""

from fastapi import APIRouter

from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.articles import router as articles_router
from app.api.v1.admin.feeds import router as feeds_router
from app.api.v1.admin.stats import router as stats_router

router = APIRouter(prefix="/admin")
router.include_router(articles_router)
router.include_router(feeds_router)
router.include_router(stats_router)
router.include_router(analytics_router)

__all__ = ["router"]
