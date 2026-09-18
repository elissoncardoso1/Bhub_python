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

import asyncio
import os
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from arq.connections import ArqRedis, RedisSettings
from arq.worker import Worker
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.jobs.tasks import WorkerSettings
from app.services import task_dispatcher

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


# --- Worker ARQ real (Task 14) -----------------------------------------------
#
# O worker que estes fixtures montam é o de PRODUÇÃO: mesmas ``functions``,
# mesmos hooks (``on_startup``/``on_job_start``/``on_job_end``/``on_shutdown``) e
# os mesmos limites (``max_jobs``/``job_timeout``/``max_tries``/``retry_jobs``/
# ``keep_result``) de ``app/jobs/tasks.py::WorkerSettings``. Nada do ARQ é
# simulado; o que muda são só duas costuras de ambiente, ambas necessárias
# porque o alvo é um Redis e um PostgreSQL que só existem DEPOIS que a fixture
# sobe o container:
#
# 1. ``redis_settings`` explícito, apontando para o container do fixture
#    ``redis_url``. ``WorkerSettings.redis_settings`` é calculado no IMPORT do
#    módulo (``app/jobs/tasks.py:19``), antes de qualquer fixture existir, logo
#    ele carrega o ``REDIS_URL`` do ambiente de quem roda a suíte.
# 2. ``ctx["session_factory"]`` apontando para o banco migrado. O startup de
#    produção instala ``app.database.async_session_maker``, criado no import a
#    partir de ``settings.database_url`` (o banco local do desenvolvedor), então
#    o job escreveria fora do banco da suíte. A injeção usa o mesmo seam que o
#    contrato dos jobs já expõe (``ctx["pdf_service"]``, T2.2) e a sessão
#    continua sendo um PostgreSQL real.
#
# O ``asyncio.wait_for`` com limite é um FAIL explícito, nunca ``skip``: um
# fixture de integração que se cala quando o worker não termina esconderia uma
# fila travada.

ARQ_BURST_TIMEOUT_SECONDS = 240.0

#: Assinatura do callable devolvido pelo fixture ``run_arq_worker``: recebe
#: ``functions`` (para um WorkerSettings local ao teste), ``settings`` (um
#: WorkerSettings local, que substitui o de produção nos limites/hooks) e
#: ``timeout``, devolve o ``Worker`` já parado com as estatísticas reais.
RunArqWorker = Callable[..., Awaitable[Worker]]


@pytest_asyncio.fixture
async def arq_pool(
    redis_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[ArqRedis, None]:
    """Liga o dispatcher ao Redis real e devolve o pool ARQ já inicializado.

    ``settings.enable_arq`` é ``False`` por default (``app/config.py:63``) e,
    nesse estado, ``get_task_queue()`` devolve ``InlineTaskQueue``
    SILENCIOSAMENTE (``app/services/task_dispatcher.py:73-79``): o Redis fica
    vazio e o código exercitado passa a ser outro (``background_tasks.
    classify_article_task`` em vez de ``ClassificationService.classify_article``)
    — um teste que esquece esta flag fica verde provando nada sobre produção.
    A flag é ligada aqui, junto do ``REDIS_URL`` do container, e os globais
    ``task_dispatcher._arq_pool`` / ``_inline_queue`` são zerados antes e depois
    para que o estado do processo não vaze entre testes (cada teste tem o seu
    event loop e um pool criado em outro loop quebra).
    """
    monkeypatch.setattr(settings, "enable_arq", True)
    monkeypatch.setattr(settings, "redis_url", redis_url)
    task_dispatcher._arq_pool = None
    task_dispatcher._inline_queue = None

    pool = await task_dispatcher.get_arq_pool()
    assert isinstance(pool, ArqRedis), (
        f"get_arq_pool() deveria devolver um pool ARQ real, devolveu {type(pool)!r}"
    )
    try:
        yield pool
    finally:
        # ``close_arq_pool`` zera o global e fecha as conexões no MESMO loop que
        # as criou; o monkeypatch das settings é restaurado depois, pelo pytest.
        await task_dispatcher.close_arq_pool()
        task_dispatcher._arq_pool = None
        task_dispatcher._inline_queue = None


@pytest_asyncio.fixture
async def run_arq_worker(
    arq_pool: ArqRedis, pg_engine: AsyncEngine, redis_url: str
) -> AsyncGenerator[RunArqWorker, None]:
    """Devolve um callable que roda um worker ARQ REAL em modo ``burst``.

    ``burst=True`` é o modo que o próprio ARQ documenta para teste
    (``arq/worker.py::async_run`` — *"Useful when testing"*): o worker processa
    a fila até esvaziá-la e RETORNA, em vez de dormir num laço infinito. A
    sincronização vem de esvaziar a fila (``zcard(queue) == 0`` + ``gather`` das
    tarefas em andamento), não de ``sleep`` arbitrário.

    O worker é criado DENTRO do event loop do teste (o ``Worker`` captura o loop
    em ``__init__``) e é função-escopado: o custo caro do startup — o MiniLM
    carregado em ``WorkerSettings.on_startup`` — é pago uma ÚNICA vez por sessão,
    porque ``EmbeddingClassifier.initialize()`` é idempotente e guarda o modelo no
    estado da classe (``app/ml/embedding_classifier.py:32``).

    O callable devolve o ``Worker`` parado, com as estatísticas reais
    (``jobs_complete``/``jobs_failed``/``jobs_retried``) para as asserções.

    ``settings`` permite um ``WorkerSettings`` LOCAL ao teste (caso ``retry`` do
    milestone 14.D: o repo não tem job que levante ``Retry``). Quando ele é
    passado, TODOS os limites/hooks do worker vêm dele — o que continua vindo
    desta fixture é só o que é preciso costurar por causa do container:
    ``redis_settings`` (o DSN do Redis do fixture, sempre) e o
    ``ctx["session_factory"]`` injetado depois do ``on_startup`` das settings.
    O ``on_startup`` das settings é chamado pelo wrapper, então settings locais
    precisam definir um (o de produção serve: carrega o MiniLM).
    """

    async def _run(
        *,
        functions: list[Any] | None = None,
        settings: Any | None = None,
        timeout: float = ARQ_BURST_TIMEOUT_SECONDS,
    ) -> Worker:
        ws = WorkerSettings if settings is None else settings
        session_factory = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

        async def _on_startup(ctx: dict[str, Any]) -> None:
            # Wiring de produção primeiro (MiniLM + sessão) e só então o banco
            # migrado do container, que não existia no import.
            await ws.on_startup(ctx)
            ctx["session_factory"] = session_factory

        worker = Worker(
            functions=ws.functions if functions is None else functions,
            redis_settings=RedisSettings.from_dsn(redis_url),
            burst=True,
            on_startup=_on_startup,
            on_shutdown=ws.on_shutdown,
            on_job_start=ws.on_job_start,
            on_job_end=ws.on_job_end,
            handle_signals=False,  # não sequestra os sinais do pytest
            max_jobs=ws.max_jobs,
            job_timeout=ws.job_timeout,
            max_tries=ws.max_tries,
            retry_jobs=ws.retry_jobs,
            keep_result=ws.keep_result,
            health_check_interval=ws.health_check_interval,
        )
        try:
            await asyncio.wait_for(worker.async_run(), timeout)
        except TimeoutError:
            pytest.fail(
                f"o worker ARQ real não esvaziou a fila em {timeout:.0f}s "
                f"(jobs_complete={worker.jobs_complete} jobs_failed={worker.jobs_failed})"
            )
        return worker

    yield _run
