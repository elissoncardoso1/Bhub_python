"""
Rotas públicas de feeds (fontes).
"""

from fastapi import APIRouter
from sqlalchemy import select, and_

from app.api.deps import DBSession
from app.models import Feed
from app.schemas import FeedListResponse, FeedResponse

router = APIRouter(prefix="/feeds", tags=["Feeds"])


@router.get("", response_model=FeedListResponse)
async def list_feeds(db: DBSession):
    """Lista todos os feeds ativos."""
    result = await db.execute(
        select(Feed)
        .where(Feed.is_active == True)
        .order_by(Feed.name)
    )
    feeds = result.scalars().all()
    
    return FeedListResponse(
        feeds=[FeedResponse.model_validate(f) for f in feeds],
        total=len(feeds)
    )


@router.get("/{feed_id}", response_model=FeedResponse)
async def get_feed(
    db: DBSession,
    feed_id: int,
):
    """Retorna detalhes de um feed."""
    result = await db.execute(
        select(Feed).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    
    if not feed:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed não encontrado",
        )
    
    return FeedResponse.model_validate(feed)
