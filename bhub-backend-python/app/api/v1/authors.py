"""
Rotas de autores.
"""

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.api.deps import DBSession
from app.models import Author
from app.schemas.author import AuthorWithStats

router = APIRouter(prefix="/authors", tags=["Authors"])


@router.get("", response_model=list[AuthorWithStats])
async def list_authors(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=100),
    search: str | None = None,
):
    """
    Lista autores, ordenados por quantidade de artigos.
    """
    stmt = select(Author).order_by(desc(Author.article_count))
    
    if search:
        stmt = stmt.where(Author.name.ilike(f"%{search}%"))
        
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    authors = result.scalars().all()
    
    return [AuthorWithStats.model_validate(a) for a in authors]
