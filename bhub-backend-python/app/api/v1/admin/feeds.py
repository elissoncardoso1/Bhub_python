"""
Rotas admin de feeds.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DBSession, Pagination
from app.core import CurrentAdmin
from app.models import Feed
from app.schemas import (
    FeedCreate,
    FeedListResponse,
    FeedResponse,
    FeedSyncAllResult,
    FeedSyncResult,
    FeedTestResult,
    FeedUpdate,
    MessageResponse,
)
from app.services import FeedAggregatorService

router = APIRouter(prefix="/feeds", tags=["Admin - Feeds"])


@router.get("", response_model=FeedListResponse)
async def admin_list_feeds(
    db: DBSession,
    admin: CurrentAdmin,
    pagination: Pagination,
    is_active: bool | None = None,
):
    """Lista todos os feeds."""
    stmt = select(Feed)
    
    if is_active is not None:
        stmt = stmt.where(Feed.is_active == is_active)
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0
    
    # Ordenar e paginar
    stmt = (
        stmt.order_by(Feed.name)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    
    result = await db.execute(stmt)
    feeds = result.scalars().all()
    
    return FeedListResponse(
        feeds=[FeedResponse.model_validate(f) for f in feeds],
        total=total,
    )


@router.post("", response_model=FeedResponse)
async def admin_create_feed(
    db: DBSession,
    admin: CurrentAdmin,
    data: FeedCreate,
):
    """Cria um novo feed."""
    # Verificar se URL já existe
    result = await db.execute(
        select(Feed).where(Feed.feed_url == data.feed_url)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feed com esta URL já existe",
        )
    
    feed = Feed(**data.model_dump())
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    
    return FeedResponse.model_validate(feed)


@router.get("/{feed_id}", response_model=FeedResponse)
async def admin_get_feed(
    db: DBSession,
    admin: CurrentAdmin,
    feed_id: int,
):
    """Retorna detalhes de um feed."""
    result = await db.execute(
        select(Feed).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed não encontrado",
        )
    
    return FeedResponse.model_validate(feed)


@router.put("/{feed_id}", response_model=FeedResponse)
async def admin_update_feed(
    db: DBSession,
    admin: CurrentAdmin,
    feed_id: int,
    data: FeedUpdate,
):
    """Atualiza um feed."""
    result = await db.execute(
        select(Feed).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed não encontrado",
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feed, field, value)
    
    await db.commit()
    await db.refresh(feed)
    
    return FeedResponse.model_validate(feed)


@router.delete("/{feed_id}", response_model=MessageResponse)
async def admin_delete_feed(
    db: DBSession,
    admin: CurrentAdmin,
    feed_id: int,
):
    """Remove um feed."""
    result = await db.execute(
        select(Feed).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed não encontrado",
        )
    
    await db.delete(feed)
    await db.commit()
    
    return MessageResponse(message="Feed removido com sucesso")


@router.post("/test", response_model=FeedTestResult)
async def admin_test_feed(
    db: DBSession,
    admin: CurrentAdmin,
    feed_url: str,
):
    """Testa um feed sem salvar."""
    service = FeedAggregatorService(db)
    result = await service.test_feed(feed_url)
    await service.close()
    
    return result


@router.post("/{feed_id}/sync", response_model=FeedSyncResult)
async def admin_sync_feed(
    db: DBSession,
    admin: CurrentAdmin,
    feed_id: int,
):
    """Sincroniza um feed específico."""
    # Verificar se existe
    result = await db.execute(
        select(Feed).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed não encontrado",
        )
    
    service = FeedAggregatorService(db)
    sync_result = await service.sync_feed(feed_id)
    await service.close()
    
    return sync_result


@router.post("/sync-all", response_model=FeedSyncAllResult)
async def admin_sync_all_feeds(
    db: DBSession,
    admin: CurrentAdmin,
):
    """Sincroniza todos os feeds ativos."""
    service = FeedAggregatorService(db)
    result = await service.sync_all_active_feeds()
    await service.close()
    
    return result
