"""
Rotas admin de artigos.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, Pagination
from app.core import CurrentAdmin
from app.models import (
    Article,
    Author,
    Category,
    Feed,
    PDFMetadata,
    ProcessingStatus,
    SourceType,
)
from app.schemas import (
    ArticleCreate,
    ArticleHighlightRequest,
    ArticleListResponse,
    ArticleResponse,
    ArticleUpdate,
    MessageResponse,
    PDFUploadResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from app.services import PDFService, WebScrapingService

router = APIRouter(prefix="/articles", tags=["Admin - Articles"])


@router.get("", response_model=ArticleListResponse)
async def admin_list_articles(
    db: DBSession,
    admin: CurrentAdmin,
    pagination: Pagination,
    category_id: int | None = None,
    feed_id: int | None = None,
    is_published: bool | None = None,
):
    """Lista todos os artigos (admin)."""
    stmt = (
        select(Article)
        .options(
            selectinload(Article.category),
            selectinload(Article.authors),
        )
    )
    
    if category_id:
        stmt = stmt.where(Article.category_id == category_id)
    
    if feed_id:
        stmt = stmt.where(Article.feed_id == feed_id)
    
    if is_published is not None:
        stmt = stmt.where(Article.is_published == is_published)
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0
    
    # Ordenar e paginar
    stmt = (
        stmt.order_by(Article.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    return ArticleListResponse.create(
        items=[ArticleResponse.model_validate(a) for a in articles],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=ArticleResponse)
async def admin_create_article(
    db: DBSession,
    admin: CurrentAdmin,
    data: ArticleCreate,
):
    """Cria um novo artigo manualmente."""
    article = Article(
        title=data.title,
        abstract=data.abstract,
        keywords=data.keywords,
        original_url=data.original_url,
        pdf_url=data.pdf_url,
        image_url=data.image_url,
        publication_date=data.publication_date,
        journal_name=data.journal_name,
        volume=data.volume,
        issue=data.issue,
        pages=data.pages,
        doi=data.doi,
        language=data.language,
        category_id=data.category_id,
        feed_id=data.feed_id,
        source_type=SourceType.MANUAL,
    )
    
    db.add(article)
    await db.flush()
    
    # Processar autores
    for author_name in data.authors:
        normalized = Author.normalize_name(author_name)
        
        result = await db.execute(
            select(Author).where(Author.normalized_name == normalized)
        )
        author = result.scalar_one_or_none()
        
        if not author:
            author = Author(name=author_name, normalized_name=normalized)
            db.add(author)
            await db.flush()
        
        article.authors.append(author)
    
    await db.commit()
    await db.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.put("/{article_id}", response_model=ArticleResponse)
async def admin_update_article(
    db: DBSession,
    admin: CurrentAdmin,
    article_id: int,
    data: ArticleUpdate,
):
    """Atualiza um artigo."""
    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.category), selectinload(Article.authors))
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )
    
    # Atualizar campos
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)
    
    await db.commit()
    await db.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.delete("/{article_id}", response_model=MessageResponse)
async def admin_delete_article(
    db: DBSession,
    admin: CurrentAdmin,
    article_id: int,
):
    """Remove um artigo."""
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )
    
    # Remover PDF se existir
    if article.pdf_file_path:
        pdf_service = PDFService()
        pdf_service.delete_pdf(article.pdf_file_path)
    
    await db.delete(article)
    await db.commit()
    
    return MessageResponse(message="Artigo removido com sucesso")


@router.patch("/{article_id}/highlight", response_model=ArticleResponse)
async def admin_toggle_highlight(
    db: DBSession,
    admin: CurrentAdmin,
    article_id: int,
    data: ArticleHighlightRequest,
):
    """Define se artigo é destacado."""
    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.category), selectinload(Article.authors))
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )
    
    article.highlighted = data.highlighted
    await db.commit()
    await db.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.post("/upload-pdf", response_model=PDFUploadResponse)
async def admin_upload_pdf(
    db: DBSession,
    admin: CurrentAdmin,
    file: UploadFile = File(...),
    category_id: int | None = None,
):
    """Upload de PDF para criar artigo."""
    
    # Validar tipo
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser um PDF",
        )
    
    pdf_service = PDFService()
    
    try:
        # Processar PDF
        pdf_data = await pdf_service.process_pdf(file.file, file.filename)
        
        # Verificar duplicata
        if await pdf_service.check_duplicate(pdf_data["file_hash"], db):
            return PDFUploadResponse(
                success=False,
                message="PDF já existe no sistema",
                duplicate=True,
            )
        
        # Buscar ou criar feed de PDFs
        from app.models import PDF_FEED_NAME, PDF_FEED_URL, FeedType
        
        result = await db.execute(
            select(Feed).where(Feed.feed_url == PDF_FEED_URL)
        )
        feed = result.scalar_one_or_none()
        
        if not feed:
            feed = Feed(
                name=PDF_FEED_NAME,
                feed_url=PDF_FEED_URL,
                feed_type=FeedType.PDF,
                is_active=False,
            )
            db.add(feed)
            await db.flush()
        
        # Criar artigo
        article = Article(
            title=pdf_data.get("title") or file.filename,
            abstract=pdf_data.get("abstract"),
            keywords=pdf_data.get("keywords"),
            doi=pdf_data.get("doi"),
            source_type=SourceType.PDF,
            feed_id=feed.id,
            category_id=category_id,
            pdf_file_path=pdf_data["file_path"],
            pdf_file_size=pdf_data["file_size"],
        )
        
        db.add(article)
        await db.flush()
        
        # Criar metadados do PDF
        metadata = PDFMetadata(
            article_id=article.id,
            file_hash=pdf_data["file_hash"],
            original_filename=pdf_data["original_filename"],
            page_count=pdf_data.get("page_count"),
            word_count=pdf_data.get("word_count"),
            extracted_text=pdf_data.get("extracted_text"),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        db.add(metadata)
        
        # Processar autores
        for author_name in pdf_data.get("authors", []):
            normalized = Author.normalize_name(author_name)
            
            result = await db.execute(
                select(Author).where(Author.normalized_name == normalized)
            )
            author = result.scalar_one_or_none()
            
            if not author:
                author = Author(name=author_name, normalized_name=normalized)
                db.add(author)
                await db.flush()
            
            article.authors.append(author)
        
        await db.commit()
        
        return PDFUploadResponse(
            success=True,
            article_id=article.id,
            message="PDF processado com sucesso",
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/scrape", response_model=ScrapeResponse)
async def admin_scrape_url(
    db: DBSession,
    admin: CurrentAdmin,
    data: ScrapeRequest,
):
    """Faz scraping de URL para criar artigo."""
    
    scraper = WebScrapingService()
    
    try:
        scraped_data = await scraper.scrape_url(data.url)
        await scraper.close()
        
        # Verificar se já existe
        result = await db.execute(
            select(Article).where(Article.external_id == scraped_data["external_id"])
        )
        if result.scalar_one_or_none():
            return ScrapeResponse(
                success=False,
                error="Artigo já existe no sistema",
            )
        
        # Buscar ou criar feed de scraping
        from app.models import SCRAPING_FEED_NAME, SCRAPING_FEED_URL, FeedType
        
        result = await db.execute(
            select(Feed).where(Feed.feed_url == SCRAPING_FEED_URL)
        )
        feed = result.scalar_one_or_none()
        
        if not feed:
            feed = Feed(
                name=SCRAPING_FEED_NAME,
                feed_url=SCRAPING_FEED_URL,
                feed_type=FeedType.SCRAPING,
                is_active=False,
            )
            db.add(feed)
            await db.flush()
        
        # Criar artigo
        article = Article(
            external_id=scraped_data["external_id"],
            title=scraped_data["title"],
            abstract=scraped_data.get("abstract"),
            keywords=scraped_data.get("keywords"),
            original_url=scraped_data["original_url"],
            doi=scraped_data.get("doi"),
            publication_date=scraped_data.get("publication_date"),
            image_url=scraped_data.get("image_url"),
            language=scraped_data.get("language", "en"),
            source_type=SourceType.SCRAPING,
            feed_id=feed.id,
            category_id=data.category_id,
        )
        
        db.add(article)
        await db.flush()
        
        # Processar autores
        for author_name in scraped_data.get("authors", []):
            normalized = Author.normalize_name(author_name)
            
            result = await db.execute(
                select(Author).where(Author.normalized_name == normalized)
            )
            author = result.scalar_one_or_none()
            
            if not author:
                author = Author(name=author_name, normalized_name=normalized)
                db.add(author)
                await db.flush()
            
            article.authors.append(author)
        
        await db.commit()
        await db.refresh(article)
        
        return ScrapeResponse(
            success=True,
            article=ArticleResponse.model_validate(article),
        )
    
    except Exception as e:
        await scraper.close()
        return ScrapeResponse(
            success=False,
            error=str(e),
        )
