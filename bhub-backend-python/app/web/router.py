"""
Router agregado do frontend SSR/HTMX.
"""

from fastapi import APIRouter

from app.web.admin import router as admin_router
from app.web.auth import router as auth_router
from app.web.routes import router as public_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(public_router)

from app.web.translation import router as translation_router

router.include_router(translation_router)

__all__ = ["router"]
