"""
Configuração do banco de dados SQLAlchemy com suporte async.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""

    pass


# Configuração do engine para SQLite async
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    # SQLite específico: usar StaticPool para conexões em memória
    poolclass=StaticPool if ":memory:" in settings.database_url else None,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in settings.database_url else {},
)

from sqlalchemy import event

# Habilitar WAL mode para SQLite
if "sqlite" in settings.database_url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# Session factory assíncrona
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que fornece uma sessão de banco de dados.
    Uso: session: AsyncSession = Depends(get_async_session)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para uso fora de rotas FastAPI.
    Uso: async with get_session_context() as session: ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Inicializa o banco de dados criando todas as tabelas.
    Também cria a tabela FTS5 para busca full-text.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Criar tabela FTS5 para busca full-text
        await conn.execute(
            text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title,
                abstract,
                keywords,
                content='articles',
                content_rowid='id'
            )
            """)
        )

        # Criar triggers para manter FTS5 sincronizado
        await conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, abstract, keywords)
                VALUES (new.id, new.title, new.abstract, new.keywords);
            END
            """)
        )

        await conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, abstract, keywords)
                VALUES ('delete', old.id, old.title, old.abstract, old.keywords);
            END
            """)
        )

        await conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, abstract, keywords)
                VALUES ('delete', old.id, old.title, old.abstract, old.keywords);
                INSERT INTO articles_fts(rowid, title, abstract, keywords)
                VALUES (new.id, new.title, new.abstract, new.keywords);
            END
            """)
        )


async def close_db() -> None:
    """Fecha todas as conexões do engine."""
    await engine.dispose()
