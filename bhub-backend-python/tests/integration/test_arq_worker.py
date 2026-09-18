"""Worker ARQ REAL contra Redis e PostgreSQL reais (Task 14 / T4.3).

Os 23 testes de integração anteriores provavam migração e busca, mas NENHUM
tocava ARQ: os 40 testes unitários de fila/dispatcher usam um ``FakeArqPool``
(``tests/unit/test_task_dispatcher.py``) sobre SQLite em memória
(``tests/conftest.py:19``). O critério do épico é "ARQ é validado além de
mocks", então aqui o caminho exercitado é o de PRODUÇÃO ponta a ponta:

    dispatcher real (``app/services/task_dispatcher.py``)
        -> Redis 7 real (container descartável do fixture ``redis_url``)
            -> worker ARQ real, burst, com as ``functions``/hooks/limites de
               ``app/jobs/tasks.WorkerSettings``
                -> PostgreSQL 16 real, migrado por ``alembic upgrade head``

Casos do milestone 14.B (o plano lista seis; retry, erro terminal e a recusa do
pool são o 14.D):

1. ``enqueue``      — o dispatcher põe um job de verdade no Redis (chave
   ``arq:job:<id>`` + membro do zset ``arq:queue``) e NÃO deduplica: dois
   despachos do mesmo artigo geram dois job ids distintos.
2. ``execução``     — um worker real pega o job, roda ``task_classify_article``
   e o job termina ``success=True`` com o resultado da classificação.
3. ``update no banco`` — o job grava em PostgreSQL de verdade
   (``articles.classification_confidence``, ``articles.category_id`` e a linha
   em ``article_categories``), com o ``commit`` do próprio job.
4. ``idempotência`` sequencial — reexecutar o mesmo artigo num segundo job não
   duplica categoria nem associação.
5. ``idempotência`` CONCORRENTE — dois despachos do MESMO artigo em voo no
   mesmo worker (``max_jobs=10``) não podem derrubar nenhum dos dois jobs nem
   duplicar o vínculo artigo↔categoria. **Este teste está VERMELHO hoje**: o
   segundo job morre com ``IntegrityError``/``UniqueViolationError`` na
   constraint ``uq_article_category``. É o RED do defeito real de produção
   (check-then-act em ``app/services/classification_service.py:234-257``, sem
   ``ON CONFLICT``, protegido só pela constraint única em
   ``app/models/article_category.py:36``); o conserto é o milestone 14.C.
6. ``retry`` (14.D)  — o MECANISMO de retry do ARQ é validado contra Redis e
   worker REAIS, com função e ``WorkerSettings`` LOCAIS ao teste: o repo não tem
   job re-tentável (ver a seção 6).
7. ``erro terminal`` (14.D) — exceção COMUM (que não é ``Retry``) levantada por
   um job REAL do repo é terminal no try 1, sem re-enfileiramento.
8. recusa do pool (14.D) — com ``ENABLE_ARQ=true`` e pool não inicializado, o
   despacho falha com o ``RuntimeError`` explícito do repo em vez de cair em
   execução local silenciosa.

Isolamento: cada teste insere e limpa as SUAS próprias linhas controladas
(``external_id`` com o prefixo ``t14-``) e apaga as chaves ARQ que criou, então
a ordem em relação a ``test_migrations.py`` — que roda ``alembic downgrade
base`` + ``upgrade head`` — não importa. Zero rede externa: sem chaves de API o
``AIManager`` não tem provedor e a classificação cai no MiniLM local, que é
carregado uma única vez por sessão.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from arq.connections import ArqRedis
from arq.constants import (
    default_queue_name,
    job_key_prefix,
    result_key_prefix,
    retry_key_prefix,
)
from arq.jobs import Job, deserialize_job
from arq.worker import Retry
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.interfaces.task_queue import CLASSIFY_JOB_NAME, ArqTaskQueue
from app.jobs.tasks import WorkerSettings
from app.models import DEFAULT_CATEGORIES, Article, Category, article_categories
from app.services import task_dispatcher
from app.services.classification_service import ClassificationService
from app.services.task_dispatcher import dispatch_classify_article
from tests.integration.conftest import RunArqWorker

pytestmark = pytest.mark.integration

# Prefixo de todo ``external_id`` controlado por esta suíte (mesma convenção de
# ``test_postgres_search.py``): é o que a limpeza usa para não tocar em linha
# alguma que não seja dela.
CONTROLLED_PREFIX = "t14-"

# Texto curto e sem relação com nenhuma categoria: o embedding fica abaixo do
# threshold (0.3) e a classificação cai em "outros". O teste NÃO prende o slug —
# ele prende que o mesmo artigo classifica IGUAL em execuções repetidas.
ARTICLE_TITLE = "Notas soltas sobre assuntos diversos"
ARTICLE_ABSTRACT = "Texto sem aderência a nenhuma categoria temática específica."


def _date() -> datetime:
    return datetime(2025, 6, 1, tzinfo=UTC)


async def _purge_controlled(session: AsyncSession) -> None:
    """Apaga só as linhas desta suíte (artigos ``t14-`` e categorias padrão).

    Artigos primeiro: a FK ``article_categories.article_id`` é ``ON DELETE
    CASCADE``, então a linha de vínculo vai junto; as categorias padrão que a
    suíte cria só podem sair depois, porque ``articles.category_id`` aponta
    para elas.
    """
    await session.execute(
        delete(Article)
        .where(Article.external_id.like(f"{CONTROLLED_PREFIX}%"))
        .execution_options(synchronize_session=False)
    )
    await session.execute(
        delete(Category)
        .where(Category.slug.in_([cat["slug"] for cat in DEFAULT_CATEGORIES]))
        .execution_options(synchronize_session=False)
    )
    await session.commit()


async def _insert_article(session: AsyncSession) -> Article:
    """Insere o artigo controlado deste teste e devolve o id dele."""
    article = Article(
        external_id=f"{CONTROLLED_PREFIX}{uuid.uuid4().hex[:8]}",
        title=ARTICLE_TITLE,
        abstract=ARTICLE_ABSTRACT,
        keywords="",
        language="pt",
        is_published=True,
        publication_date=_date(),
        journal_name="Periódico de Teste 14",
    )
    session.add(article)
    await session.commit()
    return article


async def _seed_default_categories(session: AsyncSession) -> None:
    """Pré-cria as categorias padrão pelo helper de PRODUÇÃO do serviço.

    Sem isso o teste concorrente mediria duas corridas de uma vez: a do vínculo
    artigo↔categoria e a do próprio ``get_or_create_category`` (também
    check-then-act, com ``categories.slug``/``name`` únicos). A corrida sob teste
    aqui é a do VÍNCULO — a mesma que a discovery mediu como
    ``uq_article_category`` —, então a categoria já existir isola o efeito.
    """
    for cat in DEFAULT_CATEGORIES:
        await ClassificationService.get_or_create_category(
            session,
            slug=cat["slug"],
            name=cat["name"],
            description=cat["description"],
        )
    await session.commit()


async def _links_of(session: AsyncSession, article_id: int) -> list[Any]:
    """Linhas reais de ``article_categories`` do artigo, lidas no banco.

    É um ``SELECT`` sobre a tabela de associação (não sobre entidades do ORM),
    então cada chamada devolve o estado COMMITADO no momento da leitura — não há
    cache de identidade para invalidar. Precisa porém de uma transação nova: o
    chamador não pode ter um ``SELECT`` anterior em aberto, senão o snapshot
    ficaria antes do ``commit`` do job.
    """
    result = await session.execute(
        select(article_categories).where(article_categories.c.article_id == article_id)
    )
    return list(result.all())


async def _job_result(pool: ArqRedis, job_id: str):
    """Lê o resultado real do job em Redis (``arq:result:<id>``), sem esperar."""
    return await Job(job_id, pool).result_info()


@pytest_asyncio.fixture
async def arq_redis(
    pg_session: AsyncSession, arq_pool: ArqRedis
) -> AsyncGenerator[AsyncSession, None]:
    """Sessão limpa contra o banco migrado, com as categorias padrão semeadas."""
    await _purge_controlled(pg_session)
    await _seed_default_categories(pg_session)
    yield pg_session
    try:
        await pg_session.rollback()
        await _purge_controlled(pg_session)
    except Exception as exc:  # só alcançável quando o teardown falha
        print(f"AVISO: limpeza pós-teste falhou: {exc!r}")


async def _drop_arq_keys(pool: ArqRedis, job_ids: list[str]) -> None:
    """Remove da chave e da fila os jobs que este teste criou e não vai rodar."""
    for job_id in job_ids:
        await pool.zrem(default_queue_name, job_id)
        await pool.delete(f"{job_key_prefix}{job_id}")
        await pool.delete(f"{result_key_prefix}{job_id}")


async def _retry_keys(pool: ArqRedis) -> list[str]:
    """Chaves ``arq:retry:<job_id>`` presentes no Redis (o scan devolve bytes).

    O ARQ grava essa chave ao re-tentar (``arq/worker.py:547``) e a apaga quando
    o job termina (``arq/worker.py:704,716``) — logo ela só é observável DURANTE
    as tentativas; depois de um run limpo a lista tem de estar vazia.
    """
    keys = [key async for key in pool.scan_iter(match=f"{retry_key_prefix}*")]
    return [key.decode() if isinstance(key, bytes) else key for key in keys]


# --- 1. enqueue -----------------------------------------------------------------


async def test_dispatch_enfileira_job_real_no_redis(
    arq_redis: AsyncSession, arq_pool: ArqRedis
) -> None:
    """``dispatch_classify_article`` cria um job ARQ real no Redis — e não dedupa.

    Prova o caminho ``ArqTaskQueue`` (``ENABLE_ARQ=true``, ligado pelo fixture
    ``arq_pool``): chave ``arq:job:<job_id>`` gravada, ``job_id`` presente no zset
    ``arq:queue`` e payload com a função/args do job de produção. Prova também que
    NÃO existe dedup no enfileiramento: dois despachos do mesmo artigo geram dois
    job ids distintos (``_job_id`` nunca é passado em
    ``app/interfaces/task_queue.py:46-50``) — é a raiz 2 do defeito concorrente.
    """
    article = await _insert_article(arq_redis)

    first_job_id = await dispatch_classify_article(article.id)
    second_job_id = await dispatch_classify_article(article.id)

    try:
        raw = await arq_pool.get(f"{job_key_prefix}{first_job_id}")
        assert raw is not None, (
            f"chave arq:job:{first_job_id} ausente: o dispatcher não enfileirou no Redis real"
        )
        job = deserialize_job(raw)
        assert job.function == CLASSIFY_JOB_NAME
        assert list(job.args) == [article.id]
        assert job.kwargs == {}

        score = await arq_pool.zscore(default_queue_name, first_job_id)
        assert score is not None, f"{first_job_id} não está no zset {default_queue_name}"

        assert first_job_id != second_job_id, (
            "dois despachos do mesmo artigo viraram o MESMO job id: isso exigiria um "
            "_job_id de dedup que o dispatcher não passa"
        )
        assert await arq_pool.zscore(default_queue_name, second_job_id) is not None
    finally:
        # Estes jobs não são executados neste teste: se ficassem na fila, o
        # worker do próximo teste os pegaria e as estatísticas dele mentiriam.
        await _drop_arq_keys(arq_pool, [first_job_id, second_job_id])


# --- 2. e 3. execução + update no banco -----------------------------------------


async def test_worker_real_executa_job_e_persiste_a_classificacao(
    arq_redis: AsyncSession, arq_pool: ArqRedis, run_arq_worker: RunArqWorker
) -> None:
    """Um worker ARQ real executa o job e o commit grava no PostgreSQL real.

    O job que roda é ``task_classify_article`` com o wiring de produção
    (``ctx["session_factory"]`` -> ``ctx["db"]``), e as asserções são sobre
    EFEITOS reais: o resultado em Redis (``arq:result:<id>`` com
    ``success=True``) e as três linhas/colunas no banco.
    """
    article = await _insert_article(arq_redis)
    article_id = article.id
    job_id = await dispatch_classify_article(article_id)

    worker = await run_arq_worker()

    assert worker.jobs_complete == 1
    assert worker.jobs_failed == 0

    info = await _job_result(arq_pool, job_id)
    assert info is not None, f"nenhum resultado em arq:result:{job_id}"
    assert info.success is True, f"resultado real do job: {info!r}"
    result = info.result
    assert result["article_id"] == article_id
    assert result["category"]
    assert isinstance(result["confidence"], float)
    assert await arq_pool.exists(f"{result_key_prefix}{job_id}") == 1

    # O job commitou em OUTRA conexão: `populate_existing` relê os atributos da
    # linha em vez de devolver o objeto já carregado neste teste.
    refreshed = (
        await arq_redis.execute(
            select(Article)
            .where(Article.id == article_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    persisted_confidence = refreshed.classification_confidence
    persisted_category_id = refreshed.category_id
    assert persisted_confidence == pytest.approx(result["confidence"])
    assert persisted_category_id is not None

    persisted_slug = (
        await arq_redis.execute(select(Category.slug).where(Category.id == persisted_category_id))
    ).scalar_one()
    assert persisted_slug == result["category"]

    links = await _links_of(arq_redis, article_id)
    assert len(links) == 1
    assert links[0].category_id == persisted_category_id
    assert links[0].confidence == pytest.approx(result["confidence"])
    assert links[0].is_primary is True


# --- 4. idempotência sequencial -------------------------------------------------


async def test_reexecucao_sequencial_do_mesmo_artigo_nao_duplica_a_associacao(
    arq_redis: AsyncSession, arq_pool: ArqRedis, run_arq_worker: RunArqWorker
) -> None:
    """Dois jobs do mesmo artigo, um DEPOIS do outro, não duplicam nada.

    É o caso que o teste unitário de idempotência
    (``tests/unit/test_arq_job_idempotency.py:183``) já cobre sobre SQLite; aqui
    ele é refeito no caminho REAL (worker + Redis + PostgreSQL), com o segundo
    job encontrando o vínculo já commitado pelo primeiro.
    """
    article = await _insert_article(arq_redis)
    article_id = article.id

    first_job_id = await dispatch_classify_article(article_id)
    first_worker = await run_arq_worker()
    assert first_worker.jobs_complete == 1
    assert first_worker.jobs_failed == 0

    second_job_id = await dispatch_classify_article(article_id)
    second_worker = await run_arq_worker()
    assert second_worker.jobs_complete == 1
    assert second_worker.jobs_failed == 0

    first = await _job_result(arq_pool, first_job_id)
    second = await _job_result(arq_pool, second_job_id)
    assert first is not None and second is not None
    assert first.success is True and second.success is True
    assert second.result["category"] == first.result["category"]

    links = await _links_of(arq_redis, article_id)
    assert len(links) == 1, f"reexecução duplicou o vínculo artigo↔categoria: {links}"

    categories = (
        (await arq_redis.execute(select(Category).where(Category.slug == first.result["category"])))
        .scalars()
        .all()
    )
    assert len(categories) == 1, "reexecução duplicou a categoria"


# --- 5. idempotência CONCORRENTE (RED do milestone 14.C) ------------------------


async def test_dois_dispatches_concorrentes_do_mesmo_artigo_nao_quebram_o_job(
    arq_redis: AsyncSession, arq_pool: ArqRedis, run_arq_worker: RunArqWorker
) -> None:
    """CONTRATO: despachar o mesmo artigo duas vezes não derruba job nem duplica vínculo.

    Os dois jobs ficam EM VOO no mesmo worker (``max_jobs=10``, o valor de
    produção) e disputam a mesma linha de ``article_categories``. O
    ``assign_categories_to_article`` faz check-then-act (SELECT -> INSERT) sem
    ``ON CONFLICT``, então a corrida termina em ``UniqueViolationError`` na
    constraint ``uq_article_category`` para quem chega depois — uma exceção comum,
    que o ARQ NÃO re-tenta (ele só re-tenta ``Retry``/``RetryJob``), logo o job
    termina ``success=False`` e o trabalho se perde.

    Hoje este teste FALHA: é o RED do defeito de produção e a evidência do
    milestone 14.C. Um job duplicado que se perde assim é um vínculo de
    classificação perdido em produção silenciosamente (o resultado fica 24 h no
    Redis como único rastro).
    """
    article = await _insert_article(arq_redis)
    article_id = article.id

    # Disparados juntos de propósito: `_defer_by=2` (CLASSIFY_DEFER_BY_SECONDS)
    # faz os dois vencerem no mesmo instante, então o worker os inicia na mesma
    # volta do laço — o teste mede concorrência real, não dois despachos seriais.
    job_ids = list(
        await asyncio.gather(
            dispatch_classify_article(article_id),
            dispatch_classify_article(article_id),
        )
    )
    assert len(set(job_ids)) == 2, "o dispatcher deduplicou o enfileiramento (não é o caso hoje)"

    worker = await run_arq_worker()

    results = [(job_id, await _job_result(arq_pool, job_id)) for job_id in job_ids]
    failures = [
        (job_id, type(info.result).__name__, str(info.result))
        for job_id, info in results
        if info is None or info.success is not True
    ]
    links = await _links_of(arq_redis, article_id)

    assert worker.jobs_failed == 0, (
        "despacho duplicado do mesmo artigo derrubou um job ARQ real "
        f"(jobs_complete={worker.jobs_complete} jobs_failed={worker.jobs_failed} "
        f"jobs_retried={worker.jobs_retried}): {failures}"
    )
    assert worker.jobs_complete == len(job_ids), (
        f"esperados {len(job_ids)} jobs concluídos, o worker concluiu {worker.jobs_complete}"
    )
    assert len(links) == 1, f"o vínculo artigo↔categoria foi duplicado: {links}"


# --- 6. retry: MECANISMO do ARQ validado com função/settings LOCAIS ------------
#
# O repo NÃO tem job re-tentável: o ARQ só re-enfileira ``Retry``/``RetryJob``/
# ``CancelledError`` (``arq/worker.py:613,625``) e nada sob ``app/**`` levanta
# isso — ``max_tries=3``/``retry_jobs=True`` (``app/jobs/tasks.py:168-169``) são
# configuração MORTA para os dois jobs do repo. Esse achado (RED-3 da discovery)
# é follow-up de produção e está FORA do escopo deste milestone: nada em ``app/``
# foi tocado para fazer um job do repo re-tentar.
#
# Para validar o MECANISMO contra Redis e worker REAIS, este caso registra uma
# função e um ``WorkerSettings`` LOCAIS ao arquivo de teste.

#: Tentativas observadas DENTRO do job, na ordem em que aconteceram. O worker do
#: fixture roda NO MESMO processo e o ARQ entrega a cada tentativa uma CÓPIA do
#: ``ctx`` (mutação no ``ctx`` não sobrevive à tentativa), então a lista é de
#: módulo — e o teste a limpa antes de enfileirar, para não depender de ordem.
ATTEMPTS: list[int] = []


async def _retry_once_then_succeed(ctx: dict[str, Any]) -> dict[str, Any]:
    """Job LOCAL do teste: levanta ``Retry`` no try 1 e vence no try 2.

    Cada tentativa é registrada em ``ATTEMPTS`` e o resultado devolve o
    ``job_try`` final — as duas evidências são da execução real, não do teste.
    """
    ATTEMPTS.append(ctx["job_try"])
    if ctx["job_try"] < 2:
        raise Retry(defer=0)
    return {"tentativa_final": ctx["job_try"]}


#: Nome com que o ARQ registra a função (``arq.worker.func`` usa ``__qualname__``).
RETRY_JOB_NAME = _retry_once_then_succeed.__qualname__


class RetryWorkerSettings:
    """``WorkerSettings`` LOCAL do teste: mesma configuração, função que re-tenta.

    Só ``functions`` difere de ``app/jobs/tasks.WorkerSettings``: hooks e limites
    são os de PRODUÇÃO de propósito, porque o que este caso mede é o mecanismo do
    ARQ sob a configuração real (``max_tries=3``, ``retry_jobs=True``) — a
    configuração existe e funciona; o que falta no repo é uma função que levante
    ``Retry``.

    ``redis_settings`` não é definido aqui: o ``Worker`` do fixture aponta sempre
    para o Redis do container, enquanto o ``redis_settings`` de produção é
    calculado no import a partir do ``REDIS_URL`` do ambiente (apontaria para
    fora do container). Ver ``tests/integration/conftest.py``.
    """

    functions = [_retry_once_then_succeed]
    on_startup = WorkerSettings.on_startup
    on_shutdown = WorkerSettings.on_shutdown
    on_job_start = WorkerSettings.on_job_start
    on_job_end = WorkerSettings.on_job_end
    max_jobs = WorkerSettings.max_jobs
    job_timeout = WorkerSettings.job_timeout
    max_tries = WorkerSettings.max_tries
    retry_jobs = WorkerSettings.retry_jobs
    keep_result = WorkerSettings.keep_result
    health_check_interval = WorkerSettings.health_check_interval


async def test_retry_do_arq_reenfileira_o_mesmo_job_e_vence_no_try_2(
    arq_pool: ArqRedis, run_arq_worker: RunArqWorker
) -> None:
    """PROVA o retry do ARQ com Redis + worker reais — e declara o que NÃO prova.

    PROVA: com um job cuja função levanta ``arq.Retry``, o worker REAL
    re-enfileira o MESMO job (``jobs_retried == 1``), ele é executado uma segunda
    vez com ``job_try == 2`` — as duas tentativas foram registradas DENTRO do job
    (``ATTEMPTS == [1, 2]``) e o resultado lido do Redis real traz o try final —
    e termina ``success=True``. A fila não fica com o job pendurado.

    NÃO PROVA (achado RED-3 da discovery; explicitamente FORA do escopo deste
    milestone): que os jobs do REPO re-tentem. Nenhuma função sob ``app/`` levanta
    ``Retry``/``RetryJob``/``CancelledError``, que é o ÚNICO que o ARQ
    re-enfileira (``arq/worker.py:613,625``), então ``max_tries=3`` e
    ``retry_jobs=True`` (``app/jobs/tasks.py:168-169``) são CONFIGURAÇÃO MORTA
    para ``task_classify_article``/``task_download_pdf``: qualquer exceção comum
    deles morre no try 1 — é o que a seção 7 mede. Fazer um job do repo
    re-tentar é mudança de produção e não foi feita.
    """
    ATTEMPTS.clear()
    job = await arq_pool.enqueue_job(RETRY_JOB_NAME)
    assert job is not None, f"o enfileiramento de {RETRY_JOB_NAME} não devolveu job"

    worker = await run_arq_worker(settings=RetryWorkerSettings)

    assert worker.jobs_retried == 1, (
        f"o worker não re-enfileirou o job que levantou Retry "
        f"(jobs_retried={worker.jobs_retried} jobs_failed={worker.jobs_failed} "
        f"jobs_complete={worker.jobs_complete})"
    )
    assert worker.jobs_complete == 1
    assert worker.jobs_failed == 0

    assert ATTEMPTS == [1, 2], (
        f"o job não foi executado exatamente duas vezes, com job_try 1 e 2: {ATTEMPTS}"
    )

    info = await _job_result(arq_pool, job.job_id)
    assert info is not None, f"nenhum resultado em arq:result:{job.job_id}"
    assert info.success is True, f"resultado real do job: {info!r}"
    assert info.job_try == 2, f"a segunda tentativa deveria ser job_try=2: {info.job_try}"
    assert info.result == {"tentativa_final": 2}, f"resultado real do job: {info.result!r}"

    # A chave ``arq:retry:<job_id>`` só existe DURANTE as tentativas: o ARQ a
    # apaga no finish (``arq/worker.py:704``), então depois do run não sobra nada.
    assert await _retry_keys(arq_pool) == []
    assert await arq_pool.zscore(default_queue_name, job.job_id) is None, (
        "o job retentado continuou na fila depois de terminar"
    )


# --- 7. erro terminal: exceção COMUM de um job REAL, terminal no try 1 ----------
#
# ``OUT_OF_RANGE_ARTICLE_ID`` é o gatilho REAL desta falha, sem monkeypatch de
# nada: o job de produção ``task_classify_article`` faz
# ``select(Article).where(Article.id == article_id)`` e o PostgreSQL 16 real
# recusa o parâmetro no encode (``asyncpg.DataError``: "value out of int32
# range"). A exceção sobe pelo job, passa pelo ``@observed_job`` (que a registra e
# re-levanta) e o ARQ a trata como TERMINAL, porque não é ``Retry``.
#
# MEDIÇÃO que descarta os gatilhos alternativos (probe descartável desta rodada,
# sobre a MESMA infra real): um ``article_id`` INEXISTENTE — ou uma linha apagada
# antes do worker rodar — NÃO faz o job falhar: ``classify_article`` devolve
# ``None`` e o job termina ``success=True`` com ``{'status': 'not_found'}``
# (medido: jobs_complete=1 jobs_failed=0 job_try=1); o mesmo vale para
# ``task_download_pdf`` (``{'status': 'skipped'}``). Os jobs do repo engolem os
# próprios erros de trabalho (o download captura ``httpx``/``Exception`` e devolve
# ``None``), então o erro terminal precisa ser um que a consulta do job
# realmente levanta — é este.
OUT_OF_RANGE_ARTICLE_ID = 2**31


async def test_excecao_comum_no_job_real_de_producao_termina_no_try_1(
    arq_pool: ArqRedis, run_arq_worker: RunArqWorker
) -> None:
    """PROVA: exceção comum de um job REAL do repo é terminal no try 1, sem retry.

    O job é o de PRODUÇÃO (``dispatch_classify_article`` → ``task_classify_article``
    com o wiring de ``app/jobs/tasks.py``) e a falha é um erro REAL do PostgreSQL
    levantado DENTRO dele. O worker roda com as settings de produção, sem
    override: ``max_tries=3`` e ``retry_jobs=True``. O contrato medido: exceção que
    não é ``Retry`` → ``jobs_failed=1`` no try 1, ``jobs_retried=0``, nenhuma chave
    ``arq:retry:<id>`` e nada na fila. O trabalho é PERDIDO: não existe segunda
    tentativa para uma exceção comum.

    NÃO PROVA que algum job do repo se recupere de falha (não se recupera: RED-3,
    seção 6) nem nada sobre ``job_try`` além do try 1 (terminal é sempre try 1
    aqui, nunca "max_tries esgotado", porque o ARQ só re-tenta ``Retry``).
    """
    job_id = await dispatch_classify_article(OUT_OF_RANGE_ARTICLE_ID)

    worker = await run_arq_worker()

    assert worker.jobs_failed == 1, (
        f"o job real que levantou exceção comum deveria falhar "
        f"(jobs_complete={worker.jobs_complete} jobs_failed={worker.jobs_failed} "
        f"jobs_retried={worker.jobs_retried})"
    )
    assert worker.jobs_retried == 0
    assert worker.jobs_complete == 0

    info = await _job_result(arq_pool, job_id)
    assert info is not None, f"nenhum resultado em arq:result:{job_id}"
    assert info.success is False
    assert info.job_try == 1, (
        f"a falha terminal aconteceu no try {info.job_try}: houve re-tentativa"
    )
    assert isinstance(info.result, DBAPIError), (
        f"esperado o erro real do banco levantado dentro do job, veio {info.result!r}"
    )

    assert await _retry_keys(arq_pool) == [], (
        "o ARQ gravou chave de retry (arq:retry:<job_id>) para uma exceção comum"
    )
    assert await arq_pool.zscore(default_queue_name, job_id) is None
    assert await arq_pool.exists(f"{job_key_prefix}{job_id}") == 0, (
        "a chave arq:job:<id> sobreviveu a uma falha terminal"
    )


# --- 8. recusa explícita: ENABLE_ARQ=true sem pool inicializado -----------------

#: Mensagem literal da recusa em ``app/services/task_dispatcher.py:82-89``. Copiada
#: aqui de propósito: o teste trava o TEXTO observável por quem opera. Trocar a
#: recusa explícita por um fallback silencioso quebra este teste.
POOL_NOT_INITIALIZED_ERROR = (
    "ARQ pool não inicializado — chame get_arq_pool() no startup. "
    "Recusa explícita: execução local não é permitida com ENABLE_ARQ=true."
)


async def test_despacho_com_arq_habilitado_sem_pool_recusa_explicitamente(
    arq_pool: ArqRedis,
) -> None:
    """PROVA: sem pool ARQ, o despacho falha com o erro explícito do repo.

    Com ``ENABLE_ARQ=true`` (ligado pelo fixture) e sem ``get_arq_pool()`` no
    startup, ``get_task_queue()`` entrega ``ArqTaskQueue`` com a factory
    ``_require_arq_pool`` (``app/services/task_dispatcher.py:82-89``), que recusa
    com ``RuntimeError`` e a mensagem literal do repo. O que se prova: o caminho
    de produção falha EM VOZ ALTA, em vez de (a) rodar o trabalho inline — o
    estado silencioso de ``ENABLE_ARQ=false``, que executa outro código,
    ``background_tasks.classify_article_task`` em vez de
    ``ClassificationService.classify_article`` — ou (b) enfileirar em outro lugar.

    NÃO PROVA nada sobre o lifespan do app web, que é quem chama
    ``get_arq_pool()`` no startup (``app/main.py``): aqui o pool é fechado de
    propósito para reproduzir o processo sem startup.
    """
    assert settings.enable_arq is True, "precondição: o fixture liga ENABLE_ARQ"

    # Fecha o pool do fixture e zera o global: estado de um processo em que
    # get_arq_pool() nunca rodou (ou em que close_arq_pool() já rodou).
    await task_dispatcher.close_arq_pool()
    assert task_dispatcher._arq_pool is None

    queue = task_dispatcher.get_task_queue()
    assert isinstance(queue, ArqTaskQueue), (
        f"com ENABLE_ARQ=true a fila tem de ser a ARQ, veio {type(queue)!r}"
    )

    keys_before = sorted(await arq_pool.keys(f"{job_key_prefix}*"))
    queued_before = await arq_pool.zcard(default_queue_name)

    with pytest.raises(RuntimeError) as excinfo:
        await dispatch_classify_article(1)

    assert str(excinfo.value) == POOL_NOT_INITIALIZED_ERROR
    # Nenhum fallback silencioso para execução local (o global continuaria None)…
    assert task_dispatcher._inline_queue is None
    # …e o Redis real não mudou: o despacho recusado não enfileirou nada.
    assert sorted(await arq_pool.keys(f"{job_key_prefix}*")) == keys_before
    assert await arq_pool.zcard(default_queue_name) == queued_before
