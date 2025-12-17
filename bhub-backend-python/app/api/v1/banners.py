"""
Rotas públicas de banners.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, or_, select

from app.api.deps import DBSession
from app.models import Banner, BannerPosition
from app.schemas import BannerClickRequest, BannerListResponse, BannerResponse

router = APIRouter(prefix="/banners", tags=["Banners"])


@router.get("/{position}", response_model=BannerListResponse)
async def get_banners_by_position(
    db: DBSession,
    position: BannerPosition,
):
    """Retorna banners ativos para uma posição."""
    now = datetime.utcnow()
    
    result = await db.execute(
        select(Banner)
        .where(
            Banner.position == position,
            Banner.is_active == True,
            or_(Banner.start_date.is_(None), Banner.start_date <= now),
            or_(Banner.end_date.is_(None), Banner.end_date >= now),
        )
        .order_by(Banner.priority.desc())
    )
    
    banners = result.scalars().all()
    
    # Incrementar visualizações
    for banner in banners:
        banner.view_count += 1
    await db.commit()
    
    return BannerListResponse(
        banners=[BannerResponse.model_validate(b) for b in banners]
    )


@router.post("/click")
async def track_banner_click(
    db: DBSession,
    request: BannerClickRequest,
):
    """Registra clique em um banner."""
    result = await db.execute(
        select(Banner).where(Banner.id == request.banner_id)
    )
    banner = result.scalar_one_or_none()
    
    if not banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Banner não encontrado",
        )
    
    banner.click_count += 1
    await db.commit()
    
    return {"success": True}
