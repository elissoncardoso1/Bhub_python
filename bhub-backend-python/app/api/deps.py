"""
Dependências comuns para as rotas da API.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.interfaces.services import (
    IAIManager,
    IClassificationService,
    IFeedAggregator,
    ISearchService,
)
from app.schemas import PaginationParams

# Alias para injeção de sessão do banco
DBSession = Annotated[AsyncSession, Depends(get_async_session)]
DbSession = DBSession


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


def get_ai_manager() -> IAIManager:
    """Retorna o facade de IA configurado para a aplicação."""
    from app.ai import get_ai_manager as get_configured_ai_manager

    return get_configured_ai_manager()


def get_classification_service(
    db: DBSession,
    ai: Annotated[IAIManager, Depends(get_ai_manager)],
) -> IClassificationService:
    """Cria o serviço de classificação com dependências explícitas."""
    from app.services.classification_service import ClassificationService

    return ClassificationService(db=db, ai_manager=ai)


def get_search_service(db: DBSession) -> ISearchService:
    """Cria o serviço de busca para a sessão atual."""
    from app.services.search_service import SearchService

    return SearchService(db=db)


async def get_feed_aggregator_service(
    db: DBSession,
    ai: Annotated[IAIManager, Depends(get_ai_manager)],
) -> AsyncGenerator[IFeedAggregator, None]:
    """Cria o agregador de feeds e fecha o cliente HTTP ao final da request."""
    from app.services.feed_aggregator import FeedAggregatorService

    service = FeedAggregatorService(db=db, ai_manager=ai)
    try:
        yield service
    finally:
        await service.close()


ClassifierDep = Annotated[IClassificationService, Depends(get_classification_service)]
SearchDep = Annotated[ISearchService, Depends(get_search_service)]
AIDep = Annotated[IAIManager, Depends(get_ai_manager)]
FeedAggDep = Annotated[IFeedAggregator, Depends(get_feed_aggregator_service)]
