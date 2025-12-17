"""
Router principal da API v1.
"""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.ai import router as ai_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.articles import router as articles_router
from app.api.v1.authors import router as authors_router
from app.api.v1.banners import router as banners_router
from app.api.v1.categories import router as categories_router
from app.api.v1.contact import router as contact_router
from app.api.v1.feeds import router as feeds_router
from app.api.v1.opengraph import router as opengraph_router
from app.api.v1.search import router as search_router

router = APIRouter(prefix="/api/v1")

# Rotas públicas
router.include_router(articles_router)
router.include_router(authors_router)
router.include_router(categories_router)
router.include_router(feeds_router)
router.include_router(search_router)
router.include_router(banners_router)
router.include_router(contact_router)
router.include_router(ai_router)
router.include_router(analytics_router)
router.include_router(opengraph_router)

# Rotas admin
router.include_router(admin_router)

__all__ = ["router"]
