"""
Rotas públicas de artigos.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from slowapi.util import get_remote_address
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, Pagination
from app.main import limiter
from app.models import Article, Author, Category, SourceType
from app.schemas import (
    ArticleListResponse,
    ArticleResponse,
    ArticleSearchParams,
    ArticleSimilarResponse,
    PaginatedResponse,
)
from app.services import SearchService

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=ArticleListResponse)
@limiter.limit("100/minute")
async def list_articles(
    request: Request,
    db: DBSession,
    pagination: Pagination,
    search: str | None = Query(default=None, min_length=2, max_length=200),
    category_id: list[int] | None = Query(default=None),
    author: str | None = None,
    feed_id: int | None = None,
    highlighted: bool | None = None,
    has_pdf: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str = Query(default="publication_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    strategy: str = Query(default="default", description="Strategy for listing (default, interleaved)"),
    source_category: str | None = Query(default=None, regex="^(journal|portal)$"),
):
    """Lista artigos com filtros e busca."""
    
    # Query base
    stmt = (
        select(Article)
        .where(Article.is_published == True)
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
            selectinload(Article.feed),
        )
    )
    
    # Busca full-text
    article_ids = None
    if search:
        search_service = SearchService(db)
        article_ids = await search_service.search_fts5(
            search, 
            limit=1000,  # Pegar todos os IDs relevantes
        )
        
        if not article_ids:
            # Fallback para LIKE
            article_ids = await search_service.search_like_fallback(
                search,
                limit=1000,
            )
        
        if article_ids:
            stmt = stmt.where(Article.id.in_(article_ids))
        else:
            # Nenhum resultado
            return ArticleListResponse.create(
                items=[],
                total=0,
                page=pagination.page,
                page_size=pagination.page_size,
            )
    
    # Filtros
    if category_id:
        stmt = stmt.where(Article.category_id.in_(category_id))
        
    if source_category:
        if source_category == "journal":
            # Journals are PDF/MANUAL OR have a journal_name defined (even if RSS)
            stmt = stmt.where(
                or_(
                    Article.source_type.in_([SourceType.PDF, SourceType.MANUAL]),
                    Article.journal_name.isnot(None)
                )
            )
        elif source_category == "portal":
            # Portals are RSS/SCRAPING AND have no journal_name
            stmt = stmt.where(
                and_(
                    Article.source_type.in_([SourceType.RSS, SourceType.SCRAPING]),
                    Article.journal_name.is_(None)
                )
            )
    
    if feed_id:
        stmt = stmt.where(Article.feed_id == feed_id)
    
    if highlighted is not None:
        stmt = stmt.where(Article.highlighted == highlighted)
    
    if has_pdf:
        stmt = stmt.where(Article.pdf_file_path.isnot(None))
    
    if date_from:
        stmt = stmt.where(Article.publication_date >= date_from)
    
    if date_to:
        stmt = stmt.where(Article.publication_date <= date_to)
    
    if author:
        stmt = stmt.join(Article.authors).where(
            Author.name.ilike(f"%{author}%")
        )
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0
    
    # Ordenação
    if search and article_ids:
        # Manter ordem de relevância da busca
        pass
    else:
        sort_column = getattr(Article, sort_by, Article.publication_date)
        if sort_order == "desc":
            stmt = stmt.order_by(Article.highlighted.desc(), sort_column.desc())
        else:
            stmt = stmt.order_by(Article.highlighted.desc(), sort_column.asc())
    
    # Ajustar limit para strategy interleaved para ter buffer
    current_limit = pagination.page_size
    if strategy == "interleaved":
        # Buscar mais itens para poder reordenar/filtrar
        stmt = stmt.offset(pagination.offset).limit(current_limit * 3)
    else:
        stmt = stmt.offset(pagination.offset).limit(current_limit)
    
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    # Processamento Interleaved (Penalty logic)
    if strategy == "interleaved" and articles:
        final_list = []
        delayed_list = []
        
        last_feed_id = -1  # ID impossível
        consecutive_count = 0
        MAX_CONSECUTIVE = 2
        
        for article in articles:
            # Identificar origem (Feed ID ou Journal Name se feed for None)
            current_id = article.feed_id if article.feed_id else article.journal_name
            
            if current_id == last_feed_id:
                consecutive_count += 1
            else:
                consecutive_count = 1
                last_feed_id = current_id
                
            if consecutive_count > MAX_CONSECUTIVE:
                delayed_list.append(article)
            else:
                final_list.append(article)
        
        # Reintegrar itens adiados no final (ou onde der)
        final_list.extend(delayed_list)
        
        # Cortar para o tamanho da página original
        articles = final_list[:current_limit]

    return ArticleListResponse.create(
        items=[ArticleResponse.model_validate(a) for a in articles],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/highlighted", response_model=list[ArticleResponse])
async def get_highlighted_articles(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Retorna artigos destacados."""
    result = await db.execute(
        select(Article)
        .where(
            Article.is_published == True,
            Article.highlighted == True,
        )
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
        )
        .order_by(Article.publication_date.desc())
        .limit(limit)
    )
    
    articles = result.scalars().all()
    return [ArticleResponse.model_validate(a) for a in articles]


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    db: DBSession,
    article_id: int,
):
    """Retorna detalhes de um artigo."""
    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
            selectinload(Article.pdf_metadata),
        )
    )
    
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )
    
    # Incrementar visualização
    article.view_count += 1
    await db.commit()
    
    # Refresh to reload all attributes after commit (avoid greenlet error)
    await db.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.get("/{article_id}/similar", response_model=ArticleSimilarResponse)
async def get_similar_articles(
    db: DBSession,
    article_id: int,
    limit: int = Query(default=5, ge=1, le=20),
):
    """Retorna artigos similares baseado na categoria."""
    # Buscar artigo original
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )
    
    # Buscar artigos da mesma categoria
    stmt = (
        select(Article)
        .where(
            Article.is_published == True,
            Article.id != article_id,
            Article.category_id == article.category_id,
        )
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
        )
        .order_by(Article.publication_date.desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    similar = result.scalars().all()
    
    return ArticleSimilarResponse(
        articles=[ArticleResponse.model_validate(a) for a in similar]
    )


@router.get("/{article_id}/download")
async def download_article_pdf(
    db: DBSession,
    article_id: int,
):
    """Download do PDF do artigo."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )
    
    if not article.pdf_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF não disponível",
        )
    
    pdf_path = Path(article.pdf_file_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo PDF não encontrado",
        )
    
    # Incrementar downloads
    article.download_count += 1
    await db.commit()
    
    return FileResponse(
        path=pdf_path,
        filename=f"{article.title[:50]}.pdf",
        media_type="application/pdf",
    )
