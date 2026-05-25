"""
Rotas web (SSR + HTMX) para o frontend BHUB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, Form, Query, Request
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession
from app.core.csrf import CSRFValid, get_csrf_token
from app.core.logging import log
from app.core.security import CurrentUserOptional
from app.models import Article, Category, ContactMessage, SourceType
from app.services import SearchService
from app.web.templating import get_templates

router = APIRouter(tags=["Web"])


def _is_htmx(request: Request) -> bool:
    # HTMX sends "HX-Request: true" header, but Starlette/FastAPI may lowercase it
    return request.headers.get("hx-request", "").lower() == "true" or \
           request.headers.get("HX-Request", "").lower() == "true"


@dataclass(frozen=True)
class ArticleFilters:
    search: str | None = None
    search_type: str = "text"  # "text" or "semantic"
    category_ids: tuple[int, ...] = field(default_factory=tuple)
    feed_id: int | None = None
    highlighted: bool | None = None
    has_pdf: bool | None = None
    is_open_access: bool | None = None
    source_category: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_by: str = "publication_date"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


async def _get_categories_with_counts(db: DBSession) -> list[dict]:
    stmt = (
        select(
            Category.id,
            Category.name,
            func.count(Article.id).label("article_count"),
        )
        .outerjoin(
            Article,
            and_(Article.category_id == Category.id, Article.is_published == True),
        )
        .group_by(Category.id)
        .order_by(Category.name)
    )
    result = await db.execute(stmt)
    return [
        {"id": row.id, "name": row.name, "article_count": int(row.article_count or 0)}
        for row in result.fetchall()
    ]


async def _fetch_articles(db: DBSession, filters: ArticleFilters) -> tuple[list[Article], int, int]:
    stmt = (
        select(Article)
        .where(Article.is_published == True)
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
            selectinload(Article.feed),
        )
    )

    article_ids = None
    if filters.search:
        search_service = SearchService(db)

        # Semantic search using embeddings
        if filters.search_type == "semantic":
            try:
                from app.ml import EmbeddingClassifier
                if EmbeddingClassifier.is_initialized():
                    # Use category classification as semantic search
                    # Classify the search query to find relevant category
                    category_slug, confidence = await EmbeddingClassifier.classify(filters.search)
                    if confidence > 0.3:
                        # Find category by slug
                        cat_result = await db.execute(
                            select(Category.id).where(Category.slug == category_slug)
                        )
                        cat_id = cat_result.scalar_one_or_none()
                        if cat_id:
                            # Add category filter for semantic search
                            if not filters.category_ids:
                                # If no category filter already, use semantic category
                                stmt = stmt.where(Article.category_id == cat_id)
                            # Also do text search for better results
                            article_ids = await search_service.search_fts5(filters.search, limit=1000)
                            if not article_ids:
                                article_ids = await search_service.search_like_fallback(filters.search, limit=1000)
            except Exception as e:
                log.warning(f"Semantic search failed, falling back to text search: {e}")

        # Text search (FTS5 or LIKE fallback)
        if filters.search_type == "text" or article_ids is None:
            article_ids = await search_service.search_fts5(filters.search, limit=1000)
            if not article_ids:
                article_ids = await search_service.search_like_fallback(filters.search, limit=1000)

        if article_ids:
            stmt = stmt.where(Article.id.in_(article_ids))
        elif filters.search_type == "text":
            return [], 0, 0

    if filters.category_ids:
        stmt = stmt.where(Article.category_id.in_(filters.category_ids))

    if filters.source_category:
        if filters.source_category == "journal":
            stmt = stmt.where(
                or_(
                    Article.source_type.in_([SourceType.PDF, SourceType.MANUAL]),
                    Article.journal_name.isnot(None),
                )
            )
        elif filters.source_category == "portal":
            stmt = stmt.where(
                and_(
                    Article.source_type.in_([SourceType.RSS, SourceType.SCRAPING]),
                    Article.journal_name.is_(None),
                )
            )

    if filters.feed_id:
        stmt = stmt.where(Article.feed_id == filters.feed_id)

    if filters.highlighted is not None:
        stmt = stmt.where(Article.highlighted == filters.highlighted)

    if filters.has_pdf:
        stmt = stmt.where(Article.pdf_file_path.isnot(None))

    if filters.is_open_access is not None:
        stmt = stmt.where(Article.is_open_access == filters.is_open_access)

    if filters.date_from:
        stmt = stmt.where(Article.publication_date >= filters.date_from)

    if filters.date_to:
        stmt = stmt.where(Article.publication_date <= filters.date_to)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    allowed_sort = {
        "publication_date": Article.publication_date,
        "created_at": Article.created_at,
        "impact_score": Article.impact_score,
        "view_count": Article.view_count,
        "download_count": Article.download_count,
    }
    sort_column = allowed_sort.get(filters.sort_by, Article.publication_date)

    if filters.sort_order == "asc":
        stmt = stmt.order_by(Article.highlighted.desc(), sort_column.asc())
    else:
        stmt = stmt.order_by(Article.highlighted.desc(), sort_column.desc())

    offset = (filters.page - 1) * filters.page_size
    stmt = stmt.offset(offset).limit(filters.page_size)

    result = await db.execute(stmt)
    articles = result.scalars().all()
    return list(articles), int(total), int(offset)


@router.get("/")
async def home(
    request: Request,
    db: DBSession,
    current_user: CurrentUserOptional = None,
    search: str | None = Query(default=None, max_length=200),
    category_id: list[int] | None = Query(default=None),
    feed_id: int | None = None,
    highlighted: bool | None = None,
    has_pdf: bool | None = None,
    is_open_access: bool | None = None,
    source_category: str | None = Query(default=None, pattern="^(journal|portal)$"),
    sort_by: str = Query(default="publication_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    normalized_search = (search or "").strip()
    if len(normalized_search) < 2:
        normalized_search = None

    filters = ArticleFilters(
        search=normalized_search,
        search_type="text",  # Home page only uses text search
        category_ids=tuple(category_id or []),
        feed_id=feed_id,
        highlighted=highlighted,
        has_pdf=has_pdf,
        is_open_access=is_open_access,
        source_category=source_category,
        date_from=None,
        date_to=None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    categories = await _get_categories_with_counts(db)

    # Logic for Split View vs Search View
    is_default_view = not (search or category_id or feed_id or highlighted or has_pdf or is_open_access or source_category)

    journal_articles = []
    portal_articles = []
    total_journals = 0
    total_portals = 0

    if is_default_view:
        # Fetch Journals (RSS + journal_name set)
        journal_stmt = (
            select(Article)
            .where(
                Article.is_published == True,
                Article.source_type == SourceType.RSS,
                Article.journal_name.isnot(None)
            )
            .options(selectinload(Article.category), selectinload(Article.authors), selectinload(Article.feed))
            .order_by(Article.publication_date.desc())
            .limit(20)
        )
        journal_result = await db.execute(journal_stmt)
        journal_articles = journal_result.scalars().all()

        # Fetch Portals (RSS + journal_name is None)
        portal_stmt = (
            select(Article)
            .where(
                Article.is_published == True,
                Article.source_type == SourceType.RSS,
                Article.journal_name.is_(None)
            )
            .options(selectinload(Article.category), selectinload(Article.authors), selectinload(Article.feed))
            .order_by(Article.publication_date.desc())
            .limit(20)
        )
        portal_result = await db.execute(portal_stmt)
        portal_articles = portal_result.scalars().all()

        # We don't need the main 'articles' list for the default view
        articles = []
        total = 0
    else:
        # Regular filtered search
        articles, total, _ = await _fetch_articles(db, filters)

    total_pages = max(1, (total + filters.page_size - 1) // filters.page_size) if total else 1

    context = {
        "request": request,
        "title": "Artigos",
        "csrf_token": csrf_token,
        "static_version": f"{templates.env.globals['settings'].app_version}",
        "current_user": current_user,
        "filters": filters,
        "categories": categories,
        "articles": articles,
        "journal_articles": journal_articles,
        "portal_articles": portal_articles,
        "is_default_view": is_default_view,
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "total_pages": total_pages,
    }

    if _is_htmx(request):
        # If HTMX request comes from a specific column pagination, handle it (Future)
        # For now, simplistic HTMX handling only for the main generic grid
        return templates.TemplateResponse("partials/articles/list.html", context)
    return templates.TemplateResponse("pages/home.html", context)


@router.get("/articles")
async def articles_search(
    request: Request,
    db: DBSession,
    current_user: CurrentUserOptional = None,
    search: str | None = Query(default=None, max_length=200),
    search_type: str = Query(default="text"),
    category_id: list[int] | None = Query(default=None),
    feed_id: str | None = Query(default=None),
    highlighted: str | None = Query(default=None),  # Accept string, will convert to bool
    has_pdf: str | None = Query(default=None),  # Accept string, will convert to bool
    is_open_access: str | None = Query(default=None),  # Accept string, will convert to bool
    source_category: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sort_by: str = Query(default="publication_date"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Página de busca avançada de artigos."""
    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    # Normalize and validate parameters
    normalized_search = (search or "").strip()
    if len(normalized_search) < 2:
        normalized_search = None

    # Validate and normalize search_type
    if search_type not in ("text", "semantic"):
        search_type = "text"

    # Validate and normalize source_category
    if source_category and source_category.strip() and source_category not in ("journal", "portal") or source_category and not source_category.strip():
        source_category = None

    # Validate and normalize sort_order
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    # Parse feed_id (handle empty strings)
    parsed_feed_id = None
    if feed_id and feed_id.strip():
        try:
            parsed_feed_id = int(feed_id)
        except (ValueError, TypeError):
            pass

    # Parse boolean filters (handle string "true"/"false" from checkboxes)
    parsed_highlighted = None
    if highlighted is not None:
        if isinstance(highlighted, str):
            parsed_highlighted = highlighted.lower() in ("true", "1", "yes", "on")
        else:
            parsed_highlighted = bool(highlighted)

    parsed_has_pdf = None
    if has_pdf is not None:
        if isinstance(has_pdf, str):
            parsed_has_pdf = has_pdf.lower() in ("true", "1", "yes", "on")
        else:
            parsed_has_pdf = bool(has_pdf)

    parsed_is_open_access = None
    if is_open_access is not None:
        if isinstance(is_open_access, str):
            parsed_is_open_access = is_open_access.lower() in ("true", "1", "yes", "on")
        else:
            parsed_is_open_access = bool(is_open_access)

    # Parse dates
    parsed_date_from = None
    parsed_date_to = None
    if date_from and date_from.strip():
        try:
            parsed_date_from = datetime.fromisoformat(date_from)
        except:
            pass
    if date_to and date_to.strip():
        try:
            parsed_date_to = datetime.fromisoformat(date_to)
        except:
            pass

    filters = ArticleFilters(
        search=normalized_search,
        search_type=search_type,
        category_ids=tuple(category_id or []),
        feed_id=parsed_feed_id,
        highlighted=parsed_highlighted,
        has_pdf=parsed_has_pdf,
        is_open_access=parsed_is_open_access,
        source_category=source_category,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    categories = await _get_categories_with_counts(db)

    # Get active feeds for filter
    from app.models import Feed
    feeds_result = await db.execute(
        select(Feed.id, Feed.name)
        .where(Feed.is_active == True)
        .order_by(Feed.name)
    )
    feeds = [{"id": row[0], "name": row[1]} for row in feeds_result.fetchall()]

    # Fetch articles with filters
    articles, total, _ = await _fetch_articles(db, filters)

    total_pages = max(1, (total + filters.page_size - 1) // filters.page_size) if total else 1

    context = {
        "request": request,
        "title": "Busca Avançada de Artigos",
        "csrf_token": csrf_token,
        "static_version": f"{templates.env.globals['settings'].app_version}",
        "current_user": current_user,
        "filters": filters,
        "categories": categories,
        "feeds": feeds,
        "articles": articles,
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "total_pages": total_pages,
        "search_type": search_type or "text",
    }

    if _is_htmx(request):
        return templates.TemplateResponse("partials/articles/list.html", context)
    return templates.TemplateResponse("pages/articles.html", context)


@router.get("/categories")
async def categories_page(request: Request, db: DBSession, current_user: CurrentUserOptional = None):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)
    categories = await _get_categories_with_counts(db)
    return templates.TemplateResponse(
        "pages/categories.html",
        {
            "request": request,
            "title": "Categorias",
            "csrf_token": csrf_token,
            "static_version": f"{templates.env.globals['settings'].app_version}",
            "current_user": current_user,
            "categories": categories,
        },
    )


@router.get("/search-suggestions")
async def search_suggestions(
    request: Request,
    db: DBSession,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=10, ge=1, le=20),
):
    templates = get_templates()
    normalized_search = (search or "").strip()
    if len(normalized_search) < 2:
        return templates.TemplateResponse(
            "partials/search_suggestions.html",
            {"request": request, "suggestions": []},
        )

    service = SearchService(db)
    suggestions = await service.get_suggestions(normalized_search, limit)
    return templates.TemplateResponse(
        "partials/search_suggestions.html",
        {
            "request": request,
            "suggestions": suggestions,
        },
    )


class ContactResult(BaseModel):
    success: bool
    message: str


class ContactForm(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    subject: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=10, max_length=5000)


@router.get("/about")
async def about_page(request: Request, current_user: CurrentUserOptional = None):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)
    return templates.TemplateResponse(
        "pages/about.html",
        {
            "request": request,
            "title": "Sobre",
            "csrf_token": csrf_token,
            "static_version": f"{templates.env.globals['settings'].app_version}",
            "current_user": current_user,
        },
    )


@router.get("/contact")
async def contact_page(request: Request, current_user: CurrentUserOptional = None):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)
    return templates.TemplateResponse(
        "pages/contact.html",
        {
            "request": request,
            "title": "Contato",
            "csrf_token": csrf_token,
            "static_version": f"{templates.env.globals['settings'].app_version}",
            "current_user": current_user,
            "contact_result": None,
        },
    )


@router.post("/contact")
async def contact_submit(
    request: Request,
    db: DBSession,
    current_user: CurrentUserOptional = None,
    _csrf_valid: CSRFValid = True,
    name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(default=None),
    subject: str = Form(...),
    message: str = Form(...),
):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    try:
        validated = ContactForm(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
        )
    except ValidationError as e:
        details = "; ".join(err.get("msg", "invalid") for err in e.errors())
        contact_result = ContactResult(success=False, message=f"Dados inválidos: {details}")
    else:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        db.add(
            ContactMessage(
                name=validated.name,
                email=str(validated.email),
                phone=validated.phone,
                subject=validated.subject,
                message=validated.message,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
            )
        )
        await db.commit()
        contact_result = ContactResult(
            success=True,
            message="Mensagem enviada com sucesso! Entraremos em contato em breve.",
        )

    context = {
        "request": request,
        "csrf_token": csrf_token,
        "static_version": f"{templates.env.globals['settings'].app_version}",
        "current_user": current_user,
        "contact_result": contact_result,
    }

    if _is_htmx(request):
        return templates.TemplateResponse("partials/contact/result.html", context)

    return templates.TemplateResponse(
        "pages/contact.html",
        {
            **context,
            "title": "Contato",
        },
    )


@router.get("/articles/{article_id}")
async def article_detail(
    request: Request,
    db: DBSession,
    article_id: int,
    current_user: CurrentUserOptional = None,
):
    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    result = await db.execute(
        select(Article)
        .where(Article.id == article_id, Article.is_published == True)
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
            selectinload(Article.feed),
            selectinload(Article.pdf_metadata),
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        return templates.TemplateResponse(
            "pages/not_found.html",
            {
                "request": request,
                "title": "Não encontrado",
                "csrf_token": csrf_token,
                "static_version": f"{templates.env.globals['settings'].app_version}",
                "current_user": current_user,
            },
            status_code=404,
        )

    article.view_count += 1
    await db.commit()
    await db.refresh(article)

    similar_articles: list[Article] = []
    if article.category_id:
        similar_result = await db.execute(
            select(Article)
            .where(
                Article.is_published == True,
                Article.id != article_id,
                Article.category_id == article.category_id,
            )
            .options(
                selectinload(Article.authors),
                selectinload(Article.category),
            )
            .order_by(Article.publication_date.desc())
            .limit(6)
        )
        similar_articles = list(similar_result.scalars().all())

    base_url = str(request.base_url).rstrip("/")

    # Obter metadados Open Graph
    from app.services.opengraph_service import OpenGraphService
    og_service = OpenGraphService()
    og_metadata = await og_service.get_article_metadata(article_id, base_url)

    # Preparar metadados para o template
    article_url = f"{base_url}/articles/{article_id}"
    og_image_url = og_metadata.get("og:image", f"{base_url}/api/v1/og/articles/{article_id}/image")

    return templates.TemplateResponse(
        "pages/article_detail.html",
        {
            "request": request,
            "title": article.title_translated or article.title,
            "csrf_token": csrf_token,
            "static_version": f"{templates.env.globals['settings'].app_version}",
            "current_user": current_user,
            "article": article,
            "similar_articles": similar_articles,
            "base_url": base_url,
            # Open Graph metadata
            "og_title": og_metadata.get("og:title", article.title_translated or article.title),
            "og_description": og_metadata.get("og:description", article.abstract_translated or article.abstract or ""),
            "og_image": og_image_url,
            "og_url": article_url,
            "og_type": "article",
            "twitter_card": "summary_large_image",
            "meta_description": og_metadata.get("description", article.abstract_translated or article.abstract or ""),
        },
    )
