"""Migração Alembic de banco vazio até o head, contra PostgreSQL real.

Este é o teste que o plano chama de "zero -> head": um banco Postgres vazio
recebe ``alembic upgrade head`` como o deploy faz (subprocesso real) e o esquema
resultante é inspecionado no catálogo do Postgres, não por comparação de strings.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest
import redis

pytestmark = pytest.mark.integration

# tests/integration/test_migrations.py -> tests/integration -> tests -> bhub-backend-python/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Última revisão da cadeia hoje: prova que o upgrade caminhou do zero até o head.
HEAD_REVISION = "009_feed_http_cache"

ALEMBIC_TIMEOUT_SECONDS = 300


def _asyncpg_dsn(sqlalchemy_url: str) -> str:
    """O asyncpg puro não aceita o sufixo de dialeto do SQLAlchemy."""
    return sqlalchemy_url.replace("+asyncpg", "")


def _run_alembic_upgrade(postgres_url: str) -> subprocess.CompletedProcess[str]:
    """Roda ``alembic upgrade head`` no subprocesso, exatamente como o deploy roda."""
    env = {**os.environ, "DATABASE_URL": postgres_url}
    # O ambiente exporta DEBUG=release, o que faz app.config.Settings levantar
    # ValidationError; ENVIRONMENT pode forçar caminhos de produção. Uma execução
    # de migração depende só de DATABASE_URL, então as duas são removidas.
    env.pop("DEBUG", None)
    env.pop("ENVIRONMENT", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=ALEMBIC_TIMEOUT_SECONDS,
    )


def _run_alembic_downgrade_base(postgres_url: str) -> subprocess.CompletedProcess[str]:
    """Roda ``alembic downgrade base`` no subprocesso, como um rollback de deploy.

    Mesmo tratamento de ambiente do upgrade: a execução depende só de
    ``DATABASE_URL``, então ``DEBUG``/``ENVIRONMENT`` são removidas antes.
    """
    env = {**os.environ, "DATABASE_URL": postgres_url}
    env.pop("DEBUG", None)
    env.pop("ENVIRONMENT", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=ALEMBIC_TIMEOUT_SECONDS,
    )


@pytest.fixture(scope="session")
def migrated_database(postgres_url: str) -> str:
    """Aplica a cadeia inteira no banco vazio uma única vez por sessão."""
    result = _run_alembic_upgrade(postgres_url)
    assert result.returncode == 0, (
        f"'alembic upgrade head' falhou (rc={result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    return postgres_url


async def test_articles_table_exists(migrated_database: str) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_database))
    try:
        assert await conn.fetchval("SELECT to_regclass('public.articles')") is not None
    finally:
        await conn.close()


async def test_articles_search_vector_is_tsvector(migrated_database: str) -> None:
    """Resolve o tipo pelo catálogo (pg_attribute + pg_type), não por string."""
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_database))
    try:
        typname = await conn.fetchval(
            """
            SELECT t.typname
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_type t ON t.oid = a.atttypid
            WHERE n.nspname = 'public'
              AND c.relname = 'articles'
              AND a.attname = 'search_vector'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        )
        assert typname == "tsvector", f"tipo real de articles.search_vector: {typname!r}"
    finally:
        await conn.close()


async def test_alembic_version_is_at_head(migrated_database: str) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_database))
    try:
        versions = await conn.fetchval("SELECT version_num FROM alembic_version")
        assert versions == HEAD_REVISION
    finally:
        await conn.close()


async def test_pg_trgm_extension_is_present(migrated_database: str) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_database))
    try:
        extensions = await conn.fetch("SELECT extname FROM pg_extension")
        assert "pg_trgm" in {row["extname"] for row in extensions}
    finally:
        await conn.close()


async def test_expected_indexes_exist_with_right_method(migrated_database: str) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_database))
    try:
        rows = await conn.fetch(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'articles'"
        )
        definitions = {row["indexname"]: row["indexdef"] for row in rows}

        expected_gin = ("idx_articles_search_vector", "idx_articles_title_trgm")
        for name in expected_gin:
            assert name in definitions, f"índice {name} ausente; presentes: {sorted(definitions)}"
            assert "USING gin" in definitions[name], definitions[name]

        assert "ix_articles_is_open_access" in definitions
    finally:
        await conn.close()


async def test_search_vector_trigger_exists_on_articles(migrated_database: str) -> None:
    """O trigger vem do trabalho de search_vector da migração 008."""
    conn = await asyncpg.connect(_asyncpg_dsn(migrated_database))
    try:
        triggers = await conn.fetch(
            """
            SELECT t.tgname
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = 'articles' AND NOT t.tgisinternal
            """
        )
        names = {row["tgname"] for row in triggers}
        assert "articles_search_vector_trigger" in names, f"triggers presentes: {sorted(names)}"
    finally:
        await conn.close()


async def test_upgrade_head_is_idempotent(migrated_database: str) -> None:
    """Rodar de novo num banco já migrado é no-op e continua rc=0."""
    result = _run_alembic_upgrade(migrated_database)
    assert result.returncode == 0, (
        f"segundo 'alembic upgrade head' falhou (rc={result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


def test_downgrade_base_then_upgrade_head_rebuilds_the_chain(migrated_database: str) -> None:
    """Prova que os dois comandos fecham rc=0 — não prova o estado do catálogo.

    O que é ASSERTADO aqui é só o código de saída de ``alembic downgrade base`` e do
    ``upgrade head`` seguinte. O teste NÃO inspeciona o catálogo depois do downgrade,
    então não prova que nada da aplicação sobrou: a extensão ``pg_trgm`` sobrevive de
    propósito (a 008 a cria e o downgrade dela não a derruba) e o upgrade seguinte fica
    verde em parte porque a 008 a recria com ``CREATE EXTENSION IF NOT EXISTS``. Um
    leftover que quebrasse a reconstrução — uma enumeração que o downgrade não remove,
    por exemplo, com "type ... already exists" — continuaria sendo pego por efeito
    (foi o RED que originou o teste), mas por efeito, não por asserção de catálogo.
    """
    downgrade = _run_alembic_downgrade_base(migrated_database)
    assert downgrade.returncode == 0, (
        f"'alembic downgrade base' falhou (rc={downgrade.returncode})\n"
        f"--- stdout ---\n{downgrade.stdout}\n--- stderr ---\n{downgrade.stderr}"
    )

    upgrade = _run_alembic_upgrade(migrated_database)
    assert upgrade.returncode == 0, (
        f"'alembic upgrade head' depois do downgrade base falhou (rc={upgrade.returncode})\n"
        f"--- stdout ---\n{upgrade.stdout}\n--- stderr ---\n{upgrade.stderr}"
    )


def test_redis_fixture_is_a_real_redis(redis_url: str) -> None:
    """Prova a infraestrutura compartilhada do Épico 4.

    O consumidor ARQ deste fixture chega na Task 14; aqui basta provar que é um
    Redis de verdade respondendo PING.
    """
    client = redis.from_url(redis_url)
    try:
        assert client.ping() is True
    finally:
        client.close()
