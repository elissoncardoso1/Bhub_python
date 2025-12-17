"""
Testes para rotas de artigos.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Category


@pytest.mark.asyncio
async def test_list_articles_empty(client: AsyncClient):
    """Testa listagem de artigos vazia."""
    response = await client.get("/api/v1/articles")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_articles_with_data(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Testa listagem de artigos com dados."""
    # Criar categoria
    category = Category(
        name="Clínica",
        slug="clinica",
        color="#10B981",
    )
    db_session.add(category)
    await db_session.flush()
    
    # Criar artigo
    article = Article(
        title="Test Article",
        abstract="Test abstract",
        category_id=category.id,
        is_published=True,
    )
    db_session.add(article)
    await db_session.commit()
    
    response = await client.get("/api/v1/articles")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test Article"


@pytest.mark.asyncio
async def test_get_article_not_found(client: AsyncClient):
    """Testa busca de artigo inexistente."""
    response = await client.get("/api/v1/articles/999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_highlighted_articles(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Testa busca de artigos destacados."""
    # Criar artigo destacado
    article = Article(
        title="Highlighted Article",
        highlighted=True,
        is_published=True,
    )
    db_session.add(article)
    await db_session.commit()
    
    response = await client.get("/api/v1/articles/highlighted")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(a["title"] == "Highlighted Article" for a in data)


@pytest.mark.asyncio
async def test_search_articles(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Testa busca de artigos."""
    # Criar artigos
    article1 = Article(
        title="Behavior Analysis Research",
        abstract="Study about ABA",
        is_published=True,
    )
    article2 = Article(
        title="Education Methods",
        abstract="Teaching strategies",
        is_published=True,
    )
    db_session.add_all([article1, article2])
    await db_session.commit()
    
    response = await client.get("/api/v1/articles", params={"search": "Behavior"})
    
    assert response.status_code == 200
    # Nota: FTS5 pode não estar disponível em testes, então usamos LIKE fallback


@pytest.mark.asyncio
async def test_filter_by_category(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Testa filtro por categoria."""
    # Criar categorias
    cat1 = Category(name="Clínica", slug="clinica", color="#10B981")
    cat2 = Category(name="Educação", slug="educacao", color="#3B82F6")
    db_session.add_all([cat1, cat2])
    await db_session.flush()
    
    # Criar artigos
    article1 = Article(title="Clinical Study", category_id=cat1.id, is_published=True)
    article2 = Article(title="Education Study", category_id=cat2.id, is_published=True)
    db_session.add_all([article1, article2])
    await db_session.commit()
    
    response = await client.get("/api/v1/articles", params={"category_id": cat1.id})
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Clinical Study"
