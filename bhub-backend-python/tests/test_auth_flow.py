"""
Testes adicionais de autenticação para aumentar cobertura.
"""

import pytest
from fastapi import status
from fastapi_users.password import PasswordHelper
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.refresh_token import refresh_token_service
from app.models import User, UserRole
from app.models.refresh_token import RefreshToken


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Login com credenciais válidas deve retornar access_token."""
    helper = PasswordHelper()
    user = User(
        email="login@test.com",
        hashed_password=helper.hash("password123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@test.com", "password": "password123"},
    )

    assert resp.status_code == status.HTTP_200_OK
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    """Login com senha incorreta deve retornar 401."""
    helper = PasswordHelper()
    user = User(
        email="login2@test.com",
        hashed_password=helper.hash("password123"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login2@test.com", "password": "wrong"},
    )

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json().get("detail") is not None


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(client: AsyncClient, db_session: AsyncSession):
    """Refresh deve validar token no banco e rotacionar o refresh token."""
    helper = PasswordHelper()
    user = User(
        email="login3@test.com",
        hashed_password=helper.hash("password123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login3@test.com", "password": "password123"},
    )
    assert login_resp.status_code == status.HTTP_200_OK

    old_refresh = login_resp.cookies.get("refresh_token")
    assert old_refresh is not None
    old_payload = refresh_token_service.decode_refresh_token(old_refresh)
    old_token_id = old_payload["token_id"]

    old_record = await db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_id == old_token_id)
    )
    assert old_record is not None
    assert old_record.is_active is True

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == status.HTTP_200_OK
    assert "access_token" in refresh_resp.json()

    new_refresh = refresh_resp.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != old_refresh

    new_payload = refresh_token_service.decode_refresh_token(new_refresh)
    new_token_id = new_payload["token_id"]
    assert new_token_id != old_token_id

    await db_session.refresh(old_record)
    assert old_record.is_active is False
    assert old_record.revoked_at is not None
    assert old_record.replaced_by_token_id == new_token_id

    new_record = await db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_id == new_token_id)
    )
    assert new_record is not None
    assert new_record.is_active is True

    reused_old_resp = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh},
    )
    assert reused_old_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient, db_session: AsyncSession):
    """Logout deve inativar refresh token atual no servidor."""
    helper = PasswordHelper()
    user = User(
        email="login4@test.com",
        hashed_password=helper.hash("password123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login4@test.com", "password": "password123"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    refresh_token = login_resp.cookies.get("refresh_token")
    assert refresh_token is not None

    payload = refresh_token_service.decode_refresh_token(refresh_token)
    token_id = payload["token_id"]

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        cookies={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == status.HTTP_200_OK

    token_record = await db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_id == token_id)
    )
    assert token_record is not None
    assert token_record.is_active is False
    assert token_record.revoked_at is not None

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == status.HTTP_401_UNAUTHORIZED
