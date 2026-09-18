"""Fixtures de integração: sobem containers Docker reais (PostgreSQL e Redis).

Diferente do resto da suíte, estes testes precisam de um PostgreSQL de verdade:
o objetivo é provar que a cadeia de migrações Alembic percorre do zero até o head
em um banco vazio, o que nenhum banco em memória reproduz.

Estes fixtures NUNCA fazem ``pytest.skip``. Se o Docker estiver indisponível a
suíte falha ruidosamente, porque um verde falso aqui esconderia uma migração
quebrada. Os testes são desmarcados por padrão (``-m 'not integration'`` em
``addopts``) e rodam explicitamente com ``pytest tests/integration -m integration``.

Estes fixtures também NUNCA baixam imagem: antes de cada ``docker run`` o preflight
``_require_local_image`` confere o store local, porque um ``docker run`` baixaria a
imagem do Docker Hub em silêncio e faria a suíte depender de internet externa.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

POSTGRES_IMAGE = "postgres:16-alpine"
REDIS_IMAGE = "redis:7-alpine"

# Mesmas credenciais usadas pelo docker-compose.yml do repositório.
POSTGRES_USER = "bhub"
POSTGRES_PASSWORD = "bhub"

READINESS_TIMEOUT_SECONDS = 60
DOCKER_TIMEOUT_SECONDS = 120

# tests/integration/conftest.py -> tests/integration -> tests -> bhub-backend-python/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Última revisão da cadeia hoje: prova que o upgrade caminhou do zero até o head.
HEAD_REVISION = "009_feed_http_cache"

ALEMBIC_TIMEOUT_SECONDS = 300


def _run(*args: str) -> str:
    """Roda um comando ``docker`` e devolve o stdout, sem nunca fazer skip.

    Levanta ``RuntimeError`` (com o stderr do docker) quando o binário não existe
    ou quando o comando falha — Docker ausente é erro, não teste ignorado.
    """
    try:
        result = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - exercitado só sem Docker
        raise RuntimeError(
            "Docker não encontrado no PATH; a suíte de integração exige Docker"
        ) from exc
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - exercitado só com docker travado
        raise RuntimeError(
            f"Timeout de {DOCKER_TIMEOUT_SECONDS}s em 'docker {' '.join(args)}'"
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"'docker {' '.join(args)}' falhou (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _require_local_image(image: str) -> None:
    """Falha ANTES de criar qualquer container quando a imagem não está no store local.

    ``docker run`` baixa a imagem do Docker Hub em silêncio quando ela falta, o que
    faria a suíte depender de internet externa — justamente o que os critérios de
    aceitação da Task 12 proíbem. Este preflight consulta o store local e, quando a
    imagem falta, levanta erro citando a imagem e o comando exato de
    pré-provisionamento.

    O teste NUNCA roda ``docker pull``: quem provisiona é o operador (ou o step de CI,
    explicitamente). Aqui só se verifica o que já existe.
    """
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - exercitado só sem Docker
        raise RuntimeError(
            "Docker não encontrado no PATH; a suíte de integração exige Docker"
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"imagem '{image}' não está no store local do Docker: a suíte de integração "
            "não baixa nada pela rede.\n"
            f"Pré-provisione antes de rodar: docker pull {image}\n"
            f"--- docker image inspect {image} ---\n{result.stderr.strip()}"
        )


def _force_remove(name: str) -> None:
    """Remove o container no teardown; nunca mascara o erro do corpo do teste."""
    try:
        _run("rm", "-f", name)
    except RuntimeError as exc:  # pragma: no cover - só se o daemon cair no meio
        print(f"AVISO: falha ao remover o container {name}: {exc}")


def _published_port(name: str, container_port: int) -> int:
    """Lê a porta real publicada (``docker port`` devolve ``127.0.0.1:54321``)."""
    output = _run("port", name, f"{container_port}/tcp")
    # O container pode ter mais de um binding; o primeiro é o de loopback.
    address = output.splitlines()[0].strip()
    return int(address.rsplit(":", 1)[1])


def _wait_until_ready(name: str, command: list[str], describe: str) -> None:
    """Faz polling do readiness dentro do container, com limite de 60s."""
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    last_output = "<sem saída>"
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "exec", name, *command],
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
            check=False,
        )
        last_output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(
        f"{describe} não aceitou conexões em {READINESS_TIMEOUT_SECONDS}s; "
        f"última saída: {last_output!r}"
    )


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """PostgreSQL 16 real em container descartável, com banco de nome único.

    O banco começa vazio e é exclusivo desta execução (``bhub_it_<hex>``), que é
    exatamente o que o plano exige para medir a migração ``zero -> head``.
    """
    name = f"bhub-t12-pg-{uuid.uuid4().hex[:8]}"
    database = f"bhub_it_{uuid.uuid4().hex[:8]}"
    _require_local_image(POSTGRES_IMAGE)
    _run(
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "-e",
        f"POSTGRES_USER={POSTGRES_USER}",
        "-e",
        f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
        "-e",
        f"POSTGRES_DB={database}",
        "-p",
        "127.0.0.1::5432",
        POSTGRES_IMAGE,
    )
    try:
        port = _published_port(name, 5432)
        _wait_until_ready(
            name,
            ["pg_isready", "-U", POSTGRES_USER, "-d", database],
            f"PostgreSQL {name}",
        )
        yield (
            f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@127.0.0.1:{port}/{database}"
        )
    finally:
        _force_remove(name)


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    """Redis 7 real em container descartável.

    Prova a infraestrutura compartilhada do Épico 4; o consumidor ARQ deste
    fixture chega na Task 14.
    """
    name = f"bhub-t12-redis-{uuid.uuid4().hex[:8]}"
    _require_local_image(REDIS_IMAGE)
    _run(
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "-p",
        "127.0.0.1::6379",
        REDIS_IMAGE,
    )
    try:
        port = _published_port(name, 6379)
        _wait_until_ready(name, ["redis-cli", "ping"], f"Redis {name}")
        yield f"redis://127.0.0.1:{port}/0"
    finally:
        _force_remove(name)


# --- Cadeia de migrações + sessão ORM ---------------------------------------
#
# Estes nomes nasceram em ``test_migrations.py`` (Task 12) e foram PROMOVIDOS para
# cá na Task 13: ``test_postgres_search.py`` precisa do mesmo banco migrado, e uma
# segunda cópia do caminho ``alembic upgrade head`` divergiria em silêncio. O
# comportamento é o mesmo que estava no módulo de origem.


def _asyncpg_dsn(sqlalchemy_url: str) -> str:
    """O asyncpg puro não aceita o sufixo de dialeto do SQLAlchemy."""
    return sqlalchemy_url.replace("+asyncpg", "")


def _alembic_env(postgres_url: str) -> dict[str, str]:
    """Ambiente mínimo para um subprocesso alembic: só ``DATABASE_URL`` importa.

    O ambiente do operador pode exportar ``DEBUG=release``, o que faz
    ``app.config.Settings`` levantar ValidationError; ``ENVIRONMENT`` pode forçar
    caminhos de produção. Uma execução de migração depende só de ``DATABASE_URL``,
    então as duas são removidas.
    """
    env = {**os.environ, "DATABASE_URL": postgres_url}
    env.pop("DEBUG", None)
    env.pop("ENVIRONMENT", None)
    return env


def _run_alembic_upgrade(postgres_url: str) -> subprocess.CompletedProcess[str]:
    """Roda ``alembic upgrade head`` no subprocesso, exatamente como o deploy roda."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=_alembic_env(postgres_url),
        capture_output=True,
        text=True,
        timeout=ALEMBIC_TIMEOUT_SECONDS,
    )


def _run_alembic_downgrade_base(postgres_url: str) -> subprocess.CompletedProcess[str]:
    """Roda ``alembic downgrade base`` no subprocesso, como um rollback de deploy."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        env=_alembic_env(postgres_url),
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


@pytest_asyncio.fixture
async def pg_engine(migrated_database: str) -> AsyncGenerator[AsyncEngine, None]:
    """Engine async apontando para o banco migrado, descartada ao fim do teste.

    Escopo de função de propósito: o event loop padrão dos fixtures é por função
    (``asyncio_default_fixture_loop_scope = "function"``), e um engine criado em
    outro loop quebra com "attached to a different loop". ``NullPool`` garante que
    nenhuma conexão sobreviva ao teste (o vizinho ``test_migrations.py`` pode
    derrubar e recriar o schema entre um teste e outro).
    """
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def pg_session(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Sessão ORM contra o PostgreSQL real migrado."""
    factory = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
