"""
Rotas admin de estatísticas.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DBSession
from app.core import CurrentAdmin
from app.models import Article, Author, Category, ContactMessage, Feed, PDFMetadata
from app.schemas import StatsResponse

router = APIRouter(prefix="/stats", tags=["Admin - Stats"])


@router.get("", response_model=StatsResponse)
async def get_admin_stats(
    db: DBSession,
    admin: CurrentAdmin,
):
    """Retorna estatísticas gerais do sistema."""
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    
    # Total de artigos
    total_articles = await db.scalar(
        select(func.count()).select_from(Article)
    ) or 0
    
    # Total de feeds
    total_feeds = await db.scalar(
        select(func.count()).select_from(Feed)
    ) or 0
    
    # Total de categorias
    total_categories = await db.scalar(
        select(func.count()).select_from(Category)
    ) or 0
    
    # Total de autores
    total_authors = await db.scalar(
        select(func.count()).select_from(Author)
    ) or 0
    
    # Total de PDFs
    total_pdfs = await db.scalar(
        select(func.count()).select_from(PDFMetadata)
    ) or 0
    
    # Artigos este mês
    articles_this_month = await db.scalar(
        select(func.count())
        .select_from(Article)
        .where(Article.created_at >= month_ago)
    ) or 0
    
    # Artigos esta semana
    articles_this_week = await db.scalar(
        select(func.count())
        .select_from(Article)
        .where(Article.created_at >= week_ago)
    ) or 0
    
    # Artigos destacados
    highlighted_articles = await db.scalar(
        select(func.count())
        .select_from(Article)
        .where(Article.highlighted == True)
    ) or 0
    
    # Total de visualizações
    views_total = await db.scalar(
        select(func.sum(Article.view_count))
    ) or 0
    
    # Total de downloads
    downloads_total = await db.scalar(
        select(func.sum(Article.download_count))
    ) or 0
    
    return StatsResponse(
        total_articles=total_articles,
        total_feeds=total_feeds,
        total_categories=total_categories,
        total_authors=total_authors,
        total_pdfs=total_pdfs,
        articles_this_month=articles_this_month,
        articles_this_week=articles_this_week,
        highlighted_articles=highlighted_articles,
        views_total=views_total,
        downloads_total=downloads_total,
    )


@router.get("/detailed")
async def get_detailed_stats(
    db: DBSession,
    admin: CurrentAdmin,
):
    """Retorna estatísticas detalhadas."""
    # Artigos por categoria
    category_stats = await db.execute(
        select(
            Category.name,
            func.count(Article.id).label("count")
        )
        .outerjoin(Article, Article.category_id == Category.id)
        .group_by(Category.id)
        .order_by(func.count(Article.id).desc())
    )
    
    categories = [
        {"name": row[0], "count": row[1]}
        for row in category_stats.fetchall()
    ]
    
    # Top feeds por artigos
    feed_stats = await db.execute(
        select(
            Feed.name,
            func.count(Article.id).label("count")
        )
        .outerjoin(Article, Article.feed_id == Feed.id)
        .where(Feed.is_active == True)
        .group_by(Feed.id)
        .order_by(func.count(Article.id).desc())
        .limit(10)
    )
    
    top_feeds = [
        {"name": row[0], "count": row[1]}
        for row in feed_stats.fetchall()
    ]
    
    # Top autores
    author_stats = await db.execute(
        select(
            Author.name,
            Author.article_count
        )
        .order_by(Author.article_count.desc())
        .limit(10)
    )
    
    top_authors = [
        {"name": row[0], "count": row[1]}
        for row in author_stats.fetchall()
    ]
    
    # Mensagens não lidas
    from app.models import MessageStatus
    
    unread_messages = await db.scalar(
        select(func.count())
        .select_from(ContactMessage)
        .where(ContactMessage.status == MessageStatus.UNREAD)
    ) or 0
    
    return {
        "categories": categories,
        "top_feeds": top_feeds,
        "top_authors": top_authors,
        "unread_messages": unread_messages,
    }
