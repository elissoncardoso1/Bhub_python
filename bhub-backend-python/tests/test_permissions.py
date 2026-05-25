"""
Testes de permissões - USER vs ADMIN.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


@pytest.mark.asyncio
async def test_user_cannot_access_admin_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
):
    """Testa que usuário comum não pode acessar endpoints admin."""
    import uuid

    from fastapi_users.password import PasswordHelper

    password_helper = PasswordHelper()

    # Criar usuário comum
    user = User(
        id=uuid.uuid4(),
        email="user@test.com",
        hashed_password=password_helper.hash("userpass123"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    # Login como USER
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "user@test.com",
            "password": "userpass123",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Tentar acessar endpoint admin
    admin_response = await client.get("/api/v1/admin/stats", headers=headers)

    # Deve retornar 403 Forbidden
    assert admin_response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_admin_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
):
    """Testa que admin pode acessar endpoints admin."""
    import uuid

    from fastapi_users.password import PasswordHelper

    password_helper = PasswordHelper()

    # Criar admin
    admin = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=password_helper.hash("adminpass123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()

    # Login como ADMIN
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@test.com",
            "password": "adminpass123",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Acessar endpoint admin
    admin_response = await client.get("/api/v1/admin/stats", headers=headers)

    # Deve retornar 200 OK
    assert admin_response.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_protected_endpoints(
    client: AsyncClient,
):
    """Testa que requisições sem autenticação são bloqueadas."""
    # Tentar acessar endpoint admin sem token
    admin_response = await client.get("/api/v1/admin/stats")

    # Deve retornar 401 Unauthorized
    assert admin_response.status_code == 401


@pytest.mark.asyncio
async def test_user_can_access_public_endpoints(
    client: AsyncClient,
):
    """Testa que endpoints públicos são acessíveis sem autenticação."""
    # Endpoints públicos devem ser acessíveis
    articles_response = await client.get("/api/v1/articles")
    assert articles_response.status_code == 200

    categories_response = await client.get("/api/v1/categories")
    assert categories_response.status_code == 200
