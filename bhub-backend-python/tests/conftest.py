"""
Configuração de testes com pytest.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_async_session
from app.main import app


# Engine de teste (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

async_session_test = sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Cria event loop para toda a sessão de testes."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fornece sessão de banco de dados para testes."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_test() as session:
        yield session
    
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Fornece cliente HTTP para testes."""
    
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_async_session] = override_get_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def create_test_user(db_session: AsyncSession):
    """Helper para criar usuário de teste."""
    from app.models import User, UserRole
    from passlib.hash import bcrypt
    import uuid
    
    async def _create_user(
        email: str = "test@test.com",
        password: str = "testpass123",
        role: UserRole = UserRole.USER,
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=bcrypt.hash(password),
            role=role,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    return _create_user


@pytest_asyncio.fixture
async def admin_user(create_test_user):
    """Cria usuário admin para testes."""
    from app.models import UserRole
    return await create_test_user(
        email="admin@test.com",
        password="adminpass123",
        role=UserRole.ADMIN,
    )


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, admin_user):
    """Headers de autenticação para testes."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@test.com",
            "password": "adminpass123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
