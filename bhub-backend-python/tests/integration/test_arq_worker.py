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

Casos do milestone 14.B (o plano lista seis; retry e erro terminal são o 14.D):

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
from arq.constants import default_queue_name, job_key_prefix, result_key_prefix
from arq.jobs import Job, deserialize_job
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.task_queue import CLASSIFY_JOB_NAME
from app.models import DEFAULT_CATEGORIES, Article, Category, article_categories
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
