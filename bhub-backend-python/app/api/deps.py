"""
Dependências comuns para as rotas da API.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.schemas import PaginationParams

# Alias para injeção de sessão do banco
DBSession = Annotated[AsyncSession, Depends(get_async_session)]


def get_pagination(
    page: int = Query(default=1, ge=1, description="Número da página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página"),
) -> PaginationParams:
    """Dependência para parâmetros de paginação."""
    return PaginationParams(page=page, page_size=page_size)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


async def verify_cron_secret(
    x_cron_secret: str = Header(..., alias="x-cron-secret"),
) -> bool:
    """Verifica secret para endpoints de cron."""
    if not settings.cron_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cron secret não configurado",
        )
    
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cron secret inválido",
        )
    
    return True


CronAuth = Annotated[bool, Depends(verify_cron_secret)]
