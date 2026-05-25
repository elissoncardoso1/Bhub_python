"""
Rotas web administrativas (SSR + HTMX).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DBSession
from app.core.csrf import CSRFValid, get_csrf_token
from app.core.security import CurrentAdmin
from app.models import Article, Author, Category, Feed, PDFMetadata
from app.services.feed_aggregator import FeedAggregatorService
from app.web.templating import get_templates

router = APIRouter(prefix="/admin", tags=["Web - Admin"])


class AdminActionResult(BaseModel):
    success: bool
    message: str
    details: str | None = None


@router.get("")
@router.get("/")
async def admin_dashboard(
    request: Request,
    db: DBSession,
    admin: CurrentAdmin,
):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    total_articles = await db.scalar(select(func.count()).select_from(Article)) or 0
    total_feeds = await db.scalar(select(func.count()).select_from(Feed)) or 0
    total_categories = await db.scalar(select(func.count()).select_from(Category)) or 0
    total_authors = await db.scalar(select(func.count()).select_from(Author)) or 0
    total_pdfs = await db.scalar(select(func.count()).select_from(PDFMetadata)) or 0

    articles_this_month = await db.scalar(
        select(func.count()).select_from(Article).where(Article.created_at >= month_ago)
    ) or 0
    articles_this_week = await db.scalar(
        select(func.count()).select_from(Article).where(Article.created_at >= week_ago)
    ) or 0
    highlighted_articles = await db.scalar(
        select(func.count()).select_from(Article).where(Article.highlighted == True)
    ) or 0
    views_total = await db.scalar(select(func.sum(Article.view_count))) or 0
    downloads_total = await db.scalar(select(func.sum(Article.download_count))) or 0

    stats = {
        "total_articles": int(total_articles),
        "total_feeds": int(total_feeds),
        "total_categories": int(total_categories),
        "total_authors": int(total_authors),
        "total_pdfs": int(total_pdfs),
        "articles_this_month": int(articles_this_month),
        "articles_this_week": int(articles_this_week),
        "highlighted_articles": int(highlighted_articles),
        "views_total": int(views_total),
        "downloads_total": int(downloads_total),
    }

    return templates.TemplateResponse(
        "pages/admin/dashboard.html",
        {
            "request": request,
            "title": "Admin",
            "csrf_token": csrf_token,
            "static_version": f"{templates.env.globals['settings'].app_version}",
            "current_user": admin,
            "stats": stats,
            "action_result": None,
        },
    )


@router.post("/sync-feeds")
async def admin_sync_feeds(
    request: Request,
    db: DBSession,
    admin: CurrentAdmin,
    _csrf_valid: CSRFValid = True,
):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    service = FeedAggregatorService(db)
    try:
        result = await service.sync_all_active_feeds()
    except Exception as e:
        action_result = AdminActionResult(
            success=False,
            message="Falha ao sincronizar feeds.",
            details=str(e),
        )
    else:
        action_result = AdminActionResult(
            success=True,
            message="Sincronização finalizada.",
            details=(
                f"{result.successful}/{result.total_feeds} feeds ok · "
                f"{result.failed} falhas · {result.new_articles} novos artigos · "
                f"{result.duration_seconds:.1f}s"
            ),
        )
    finally:
        await service.close()

    return templates.TemplateResponse(
        "partials/admin/action_result.html",
        {
            "request": request,
            "csrf_token": csrf_token,
            "static_version": f"{templates.env.globals['settings'].app_version}",
            "current_user": admin,
            "action_result": action_result,
        },
    )
