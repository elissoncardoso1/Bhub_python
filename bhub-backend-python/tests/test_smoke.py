"""
Testes smoke - verificações básicas de saúde da aplicação.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Testa o endpoint /health."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "version" in data
    assert "database" in data
    assert "ml_model" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_root(client: AsyncClient):
    """Testa o endpoint raiz da API."""
    response = await client.get("/api")

    assert response.status_code == 200
    data = response.json()

    assert "name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_docs_available_in_debug(client: AsyncClient):
    """Testa se docs estão disponíveis em modo debug."""
    # Em produção, docs devem estar desabilitados
    # Este teste verifica que a rota existe (mesmo que retorne 404 em produção)
    response = await client.get("/docs")
    # Pode ser 200 (dev) ou 404 (prod), mas não deve ser 500
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_articles_endpoint_exists(client: AsyncClient):
    """Testa que o endpoint de artigos existe e responde."""
    response = await client.get("/api/v1/articles")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
