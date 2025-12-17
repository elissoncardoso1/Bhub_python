"""
Rotas de categorias.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DBSession
from app.models import Article, Category
from app.schemas import CategoryListResponse, CategoryResponse, CategoryWithStats

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=CategoryListResponse)
async def list_categories(db: DBSession):
    """Lista todas as categorias."""
    result = await db.execute(
        select(Category).order_by(Category.name)
    )
    categories = result.scalars().all()
    
    # Contar artigos por categoria
    responses = []
    for cat in categories:
        count_result = await db.execute(
            select(func.count())
            .select_from(Article)
            .where(
                Article.category_id == cat.id,
                Article.is_published == True,
            )
        )
        article_count = count_result.scalar() or 0
        
        response = CategoryResponse.model_validate(cat)
        response.article_count = article_count
        responses.append(response)
    
    return CategoryListResponse(categories=responses)


@router.get("/{category_id}", response_model=CategoryWithStats)
async def get_category(
    db: DBSession,
    category_id: int,
):
    """Retorna detalhes de uma categoria."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    
    # Contar artigos
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    
    total_result = await db.execute(
        select(func.count())
        .select_from(Article)
        .where(
            Article.category_id == category_id,
            Article.is_published == True,
        )
    )
    
    month_result = await db.execute(
        select(func.count())
        .select_from(Article)
        .where(
            Article.category_id == category_id,
            Article.is_published == True,
            Article.created_at >= month_ago,
        )
    )
    
    week_result = await db.execute(
        select(func.count())
        .select_from(Article)
        .where(
            Article.category_id == category_id,
            Article.is_published == True,
            Article.created_at >= week_ago,
        )
    )
    
    response = CategoryWithStats.model_validate(category)
    response.article_count = total_result.scalar() or 0
    response.articles_this_month = month_result.scalar() or 0
    response.articles_this_week = week_result.scalar() or 0
    
    return response


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    db: DBSession,
    slug: str,
):
    """Retorna categoria pelo slug."""
    result = await db.execute(
        select(Category).where(Category.slug == slug)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    
    return CategoryResponse.model_validate(category)
