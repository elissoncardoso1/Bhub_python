"""
Rotas de busca.
"""

from fastapi import APIRouter, Query

from app.api.deps import SearchDep

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/suggestions")
async def get_search_suggestions(
    search_service: SearchDep,
    q: str = Query(..., min_length=2, max_length=100, description="Termo de busca"),
    limit: int = Query(default=10, ge=1, le=20),
) -> list[str]:
    """Retorna sugestões de busca baseadas no termo."""
    suggestions = await search_service.get_suggestions(q, limit)
    return suggestions


@router.get("/stats")
async def get_search_stats(
    search_service: SearchDep,
) -> dict:
    """Retorna estatísticas do sistema de busca."""
    return await search_service.get_search_stats()
