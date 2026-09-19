"""Feed RSS -> PostgreSQL -> Redis/ARQ, ponta a ponta e SEM internet externa (Task 15 / T4.4).

O épico 4 do plano pede o fluxo de ingestão controlado:

    RSS -> FeedAggregatorService -> Article -> commit -> dispatch ARQ

e cinco validações literais (``docs/superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md``,
seção "Task 15", linha 1077):

(a) artigo persistido;
(b) autores associados;
(c) job disparado SOMENTE depois do commit;
(d) duplicata não gera novo artigo;
(e) entrada inválida não aborta o feed inteiro.

Nada aqui é dublê de banco ou fila: o PostgreSQL 16 e o Redis 7 são containers
reais dos fixtures de ``tests/integration/conftest.py`` (o mesmo ``alembic upgrade
head`` já aplicado em ``migrated_database``), e o enfileiramento passa pelo
dispatcher de produção (``app/services/task_dispatcher.py`` -> ``ArqTaskQueue`` ->
Redis real). O único componente que NÃO é real é a internet: o feed é servido por
``httpx.MockTransport`` injetado no ``FeedFetcher``/``FeedAggregatorService``
(``http_client=``), que responde em memória — o transporte não abre socket nenhum,
logo a suíte satisfaz "não depende de internet externa" por construção, e não por
monkeypatch de rede. O que o "servidor" recebeu (e o que NÃO estava no mapa de
payloads) é registrado e conferido em ``test_feed_persiste_artigos_...``.

Decisões de medição que valem a leitura antes de mexer:

- **O despacho é observado DENTRO do fluxo, por conexão independente.** O teste (c)
  não conclui ordem pelo texto do serviço: ele troca os globais de módulo
  ``feed_aggregator.dispatch_classify_article``/``dispatch_download_pdf`` por uma
  sonda que, no instante da chamada, LÊ o artigo por um engine SEPARADO (NullPool,
  outra conexão) e só depois chama o dispatcher real. Pré-commit essa leitura não
  enxerga nada; pós-commit enxerga. A sonda não substitui o enfileiramento — o job
  vai para o Redis real e é conferido lá (``arq:job:<id>`` + membro do zset
  ``arq:queue``).
- **Risco REGISTRADO, não corrigido (fora do escopo desta task):** não existe
  outbox entre o commit e o despacho. Se o processo morrer nessa janela, o artigo
  fica persistido e o job de classificação se perde. A ordem está correta e é o
  que este teste prende; a atomicidade não existe e nenhuma linha de ``app/`` foi
  mudada para fabricá-la.
- **A chave de deduplicação é POR FEED:** ``feed_{feed_id}_{md5(guid)}``
  (``ArticleParserService.generate_external_id``), com pré-checagem em
  ``_process_feed_entry``. O MESMO guid em OUTRO feed é artigo novo, de propósito.
  O único backstop global é a unique de ``articles.doi`` — por isso as asserções
  prendem a semântica por feed (medida) em vez de supor dedupe global.
- **Falso-verde do caminho inline:** ``ENABLE_ARQ=false`` (o default de
  ``app/config.py:63``) faz ``get_task_queue()`` devolver ``InlineTaskQueue`` em
  silêncio e NADA chega ao Redis. Por isso toda asserção de despacho passa por
  ``_assert_jobs_no_redis_real`` (chaves reais + recusa de job id ``inline-``), e
  ``test_guarda_de_chaves_no_redis_rejeita_o_caminho_inline`` prova que essa guarda
  REJEITA o caminho inline — sem ela, a suíte poderia ficar verde provando nada.
- **Isolamento:** cada teste cria os SEUS feeds (``t15-``), artigos (``external_id``
  derivado do feed), autores (nome com prefixo ``T15 ``) e jobs; o teardown apaga
  essa lista e as chaves ARQ correspondentes. Feeds/artigos não são reaproveitados
  entre testes, então ``test_migrations.py`` (que roda ``downgrade base`` +
  ``upgrade head``) pode rodar antes ou depois sem afetar nada. Categorias não são
  apagadas no teardown: são dado de referência compartilhado com outros testes.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import pytest_asyncio
from arq.connections import ArqRedis
from arq.constants import default_queue_name, job_key_prefix, result_key_prefix
from arq.jobs import Job
from sqlalchemy import Row, delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.interfaces.task_queue import ArqTaskQueue, InlineTaskQueue
from app.models import (
    DEFAULT_CATEGORIES,
    Article,
    Author,
    Feed,
    FeedType,
    SourceType,
    article_authors,
    article_categories,
)
from app.services import feed_aggregator, task_dispatcher
from app.services.article_parser import ArticleParserService
from app.services.classification_service import ClassificationService
from app.services.feed_aggregator import FeedAggregatorService
from app.services.feed_fetcher import FeedFetcher
from app.services.task_dispatcher import (
    dispatch_classify_article as real_dispatch_classify_article,
)
from app.services.task_dispatcher import (
    dispatch_download_pdf as real_dispatch_download_pdf,
)
from tests.integration.conftest import RunArqWorker

pytestmark = pytest.mark.integration

#: Host dos payloads controlados. NÃO é resolvido por DNS: o único transporte do
#: teste é o ``httpx.MockTransport`` injetado.
FEED_HOST = "mock15.local"
FEED_URL_ALFA = f"https://{FEED_HOST}/feed-alfa.xml"
FEED_URL_BETA = f"https://{FEED_HOST}/feed-beta.xml"
FEED_URL_GAMA = f"https://{FEED_HOST}/feed-gama.xml"
FEED_URL_DELTA = f"https://{FEED_HOST}/feed-delta.xml"

#: Prefixo de todo dado controlado por esta suíte (autores; feeds por nome).
AUTHOR_PREFIX = "T15 "

#: DOI do artigo-semente e da entrada que colide com ele (teste (e)).
DOI_COLIDENTE = "10.1590/t15-invalido"


# --- Feed pequeno e controlado ------------------------------------------------


def _item(
    *,
    guid: str,
    title: str,
    link: str,
    creators: tuple[str, ...] = (),
    extra: str = "",
) -> str:
    """Um ``<item>`` do feed de teste, com os campos que o parser realmente lê."""
    creators_xml = "".join(f"<dc:creator>{name}</dc:creator>" for name in creators)
    return (
        "<item>"
        f"<title>{title}</title>"
        f"<link>{link}</link>"
        f'<guid isPermaLink="false">{guid}</guid>'
        f"<description>Resumo controlado de {title}.</description>"
        f"{creators_xml}"
        f"{extra}"
        "<pubDate>Mon, 01 Jun 2026 12:00:00 GMT</pubDate>"
        "</item>"
    )


def _feed_xml(*items: str) -> str:
    """Feed RSS 2.0 mínimo (canal + itens), no dialeto ``dc:`` medido no parser."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<channel>"
        "<title>Feed Controlado T15</title>"
        f"<link>https://{FEED_HOST}/</link>"
        "<description>Feed pequeno e controlado da suite de integracao T4.4</description>"
        f"{''.join(items)}"
        "</channel></rss>"
    )


# --- Conexão INDEPENDENTE para ler o que foi commitado -------------------------


class Verifier:
    """Engine próprio (``NullPool``) para ler o banco por FORA da sessão do teste.

    A sessão do teste tem a transação e o cache de identidade do ORM. Uma linha
    adicionada com ``flush`` é visível NELA antes do commit — então medir
    "persistido" ou "commitado antes do despacho" com a própria sessão não prova
    nada. Este engine é outro: cada leitura é uma conexão nova e só enxerga dado
    COMMITADO.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _rows(self, statement: Any) -> list[Any]:
        async with self._engine.connect() as conn:
            result = await conn.execute(statement)
            return list(result.all())

    async def article_exists(self, article_id: int) -> bool:
        rows = await self._rows(select(Article.id).where(Article.id == article_id))
        return bool(rows)

    async def articles_of_feed(self, feed_id: int) -> list[Row[Any]]:
        """``(id, title, external_id, doi, confidence, category_id)`` por id."""
        return await self._rows(
            select(
                Article.id,
                Article.title,
                Article.external_id,
                Article.doi,
                Article.classification_confidence,
                Article.category_id,
            )
            .where(Article.feed_id == feed_id)
            .order_by(Article.id)
        )

    async def author_links(self, article_id: int) -> list[Row[Any]]:
        """``(name, normalized_name, position, role)`` de ``article_authors`` real."""
        return await self._rows(
            select(
                Author.name,
                Author.normalized_name,
                article_authors.c.position,
                article_authors.c.role,
            )
            .select_from(article_authors)
            .join(Author, Author.id == article_authors.c.author_id)
            .where(article_authors.c.article_id == article_id)
            .order_by(article_authors.c.position)
        )

    async def category_links(self, article_id: int) -> list[Row[Any]]:
        return await self._rows(
            select(
                article_categories.c.category_id,
                article_categories.c.confidence,
                article_categories.c.is_primary,
            ).where(article_categories.c.article_id == article_id)
        )

    async def feed_stats(self, feed_id: int) -> Row[Any]:
        """``(error_count, last_error, articles_last_sync, total_articles)``."""
        rows = await self._rows(
            select(
                Feed.error_count,
                Feed.last_error,
                Feed.articles_last_sync,
                Feed.total_articles,
            ).where(Feed.id == feed_id)
        )
        assert rows, f"feed {feed_id} não existe no banco migrado"
        return rows[0]


@pytest_asyncio.fixture
async def verifier(migrated_database: str) -> AsyncGenerator[Verifier, None]:
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield Verifier(engine)
    finally:
        await engine.dispose()


# --- A "fila real" e a guarda anti-falso-verde ---------------------------------

#: Como o ``InlineTaskQueue`` nomeia os jobs que NÃO vão para o Redis
#: (``app/interfaces/task_queue.py:103,119``): ``inline-classify-<id>``.
INLINE_JOB_ID_HINT = "inline-"


async def _assert_jobs_no_redis_real(pool: ArqRedis, job_ids: Sequence[str]) -> None:
    """Guarda de TODA asserção de despacho desta suíte: o job existe no Redis REAL.

    Falha quando o job foi "despachado" pelo caminho inline (``ENABLE_ARQ=false``
    troca a fila em silêncio e o Redis fica vazio) ou quando o dispatcher não
    enfileirou nada. Isso é o que impede a suíte de ficar verde provando nada:
    ``test_guarda_de_chaves_no_redis_rejeita_o_caminho_inline`` chama esta função
    com um job id do caminho inline e exige o ``AssertionError``.
    """
    assert job_ids, "nenhum job foi despachado: nada para conferir no Redis"
    for job_id in job_ids:
        assert not job_id.startswith(INLINE_JOB_ID_HINT), (
            f"job id {job_id!r} é do caminho inline (ENABLE_ARQ=false): "
            "o trabalho NÃO passou pelo Redis/ARQ real"
        )
        key = f"{job_key_prefix}{job_id}"
        assert await pool.exists(key) == 1, (
            f"chave {key} ausente: o despacho não chegou ao Redis real"
        )
        assert await pool.zscore(default_queue_name, job_id) is not None, (
            f"{job_id} não está no zset {default_queue_name}"
        )


async def _drop_arq_keys(pool: ArqRedis, job_ids: Sequence[str]) -> None:
    """Remove da fila e do Redis os jobs controlados por esta suíte."""
    for job_id in job_ids:
        await pool.zrem(default_queue_name, job_id)
        await pool.delete(f"{job_key_prefix}{job_id}")
        await pool.delete(f"{result_key_prefix}{job_id}")


# --- Fixture do pipeline: feed controlado + sonda de despacho + limpeza --------


class FeedPipeline:
    """Estado de UM teste: sessão, feed em memória, rastros de despacho e limpeza."""

    def __init__(self, session: AsyncSession, verifier: Verifier) -> None:
        self.session = session
        self.verifier = verifier
        self.payloads: dict[str, str] = {}
        self.served: list[str] = []
        self.unexpected: list[str] = []
        self.feed_ids: list[int] = []
        self.job_ids: list[str] = []
        self.trace: list[str] = []
        self.enqueued: list[str] = []
        self._clients: list[httpx.AsyncClient] = []

    # -- "servidor" HTTP em memória ------------------------------------------

    def _handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        payload = self.payloads.get(url)
        if payload is None:
            self.unexpected.append(url)
            return httpx.Response(404, text="URL fora do mapa controlado desta suite")
        self.served.append(url)
        return httpx.Response(
            200,
            text=payload,
            headers={
                "etag": '"t15-etag"',
                "last-modified": "Mon, 01 Jun 2026 12:00:00 GMT",
            },
        )

    def build_service(self, feed_url: str, xml: str) -> FeedAggregatorService:
        """Serviço REAL com o transporte HTTP trocado por ``MockTransport``.

        O ``http_client=`` é injetado de propósito: além do fetch do feed, ele é
        quem o fallback de scraping de autores usaria, então injetá-lo garante que
        nenhum caminho deste teste abra socket.
        """
        self.payloads[feed_url] = xml
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(self._handler),
            timeout=30.0,
            follow_redirects=True,
        )
        self._clients.append(client)
        return FeedAggregatorService(
            db=self.session,
            http_client=client,
            fetcher=FeedFetcher(client=client),
        )

    # -- banco ---------------------------------------------------------------

    async def create_feed(self, feed_url: str, *, name: str) -> Feed:
        feed = Feed(
            name=name,
            journal_name="Revista de Teste 15",
            feed_url=feed_url,
            feed_type=FeedType.RSS,
            is_active=True,
        )
        self.session.add(feed)
        await self.session.commit()
        assert feed.id is not None, "o feed controlado não recebeu id"
        self.feed_ids.append(feed.id)
        return feed

    async def seed_article_with_doi(self, feed: Feed, doi: str) -> Article:
        """Artigo já COMMITADO com um DOI, para colidir com uma entrada inválida."""
        article = Article(
            external_id=f"t15-semente-{uuid.uuid4().hex[:8]}",
            title="Artigo Semente com DOI",
            abstract="Semente do teste de entrada invalida.",
            language="pt",
            doi=doi,
            source_type=SourceType.RSS,
            feed_id=feed.id,
            publication_date=datetime(2026, 6, 1, tzinfo=UTC),
        )
        self.session.add(article)
        await self.session.commit()
        assert article.id is not None
        return article

    # -- sonda de despacho (validação (c)) ----------------------------------

    def spy_dispatches_with_ordering(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Envolve os dois despachos medindo a visibilidade do artigo NO INSTANTE.

        A sonda é fina de propósito: ela MEDE (visibilidade por conexão
        independente) e então chama o dispatcher REAL, devolvendo o job id real —
        o enfileiramento verificado depois é o de produção, não um dublê.
        """

        async def _spy_classify(article_id: int) -> str:
            await self._record_dispatch("classify", article_id)
            job_id = await real_dispatch_classify_article(article_id)
            self.job_ids.append(job_id)
            self.enqueued.append(f"classify: job={job_id}")
            return job_id

        async def _spy_pdf(article_id: int, pdf_url: str | None = None) -> str:
            await self._record_dispatch("download_pdf", article_id, pdf_url)
            job_id = await real_dispatch_download_pdf(article_id, pdf_url)
            self.job_ids.append(job_id)
            self.enqueued.append(f"download_pdf: job={job_id}")
            return job_id

        monkeypatch.setattr(feed_aggregator, "dispatch_classify_article", _spy_classify)
        monkeypatch.setattr(feed_aggregator, "dispatch_download_pdf", _spy_pdf)

    async def _record_dispatch(self, kind: str, article_id: int, *rest: Any) -> None:
        visible = await self.verifier.article_exists(article_id)
        self.trace.append(
            f"{kind}: artigo={article_id} visivel_em_outra_conexao={visible} extra={rest!r}"
        )
        assert visible, (
            "despacho ANTES do commit: o artigo "
            f"{article_id} não está visível em outra conexão no instante do "
            f"despacho {kind} (trace={self.trace})"
        )


async def _purge_controlled(session: AsyncSession, feed_ids: Sequence[int]) -> None:
    """Apaga SÓ as linhas desta suíte: vínculos, artigos, autores e feeds.

    O ``rollback`` inicial existe por dois motivos: descartar o que o teste deixou
    pendente e SOLTAR os locks da sessão (o teste que injeta falha de commit fica
    com a transação aberta, com linha travada).

    O commit final é chamado pela CLASSE de propósito: ``test_commit_que_falha_...``
    troca o ``commit`` da INSTÂNCIA por um que levanta erro, e esta fixture é
    finalizada antes de o ``monkeypatch`` desfazer a troca — um ``session.commit()``
    normal aqui cairia no fake e a limpeza nunca commitaria (a linha sobreviveria e
    o próximo teste morreria com unique violation em ``feeds.feed_url``).
    """
    await session.rollback()
    if feed_ids:
        article_ids = select(Article.id).where(Article.feed_id.in_(feed_ids))
        await session.execute(
            delete(article_authors).where(article_authors.c.article_id.in_(article_ids))
        )
        await session.execute(
            delete(article_categories)
            .where(article_categories.c.article_id.in_(article_ids))
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(Article)
            .where(Article.feed_id.in_(feed_ids))
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(Feed).where(Feed.id.in_(feed_ids)).execution_options(synchronize_session=False)
        )
    # Autores: só os desta suíte (prefixo de nome). As categorias ficam de fora de
    # propósito — são dado de referência compartilhado com o resto da suíte.
    await session.execute(
        delete(Author)
        .where(Author.name.like(f"{AUTHOR_PREFIX}%"))
        .execution_options(synchronize_session=False)
    )
    await AsyncSession.commit(session)


@pytest_asyncio.fixture
async def feed_pipeline(
    pg_session: AsyncSession,
    verifier: Verifier,
    arq_pool: ArqRedis,
) -> AsyncGenerator[FeedPipeline, None]:
    """Pipeline controlado, com limpeza das linhas e das chaves ARQ que ele criou.

    ``arq_pool`` é dependência explícita (mesmo sem uso direto) porque o fixture
    dele é quem liga ``ENABLE_ARQ`` e aponta o dispatcher para o Redis do
    container: sem ele o despacho cairia no executor inline.
    """
    pipeline = FeedPipeline(pg_session, verifier)
    jobs_at_start = set(await _arq_job_ids(arq_pool))
    try:
        yield pipeline
    finally:
        try:
            # Só o que ESTE teste criou: a diferença contra o snapshot do setup mais
            # os ids que a própria sonda registrou (o job de um vizinho não é tocado).
            criados = sorted(set(await _arq_job_ids(arq_pool)) - jobs_at_start)
            await _drop_arq_keys(arq_pool, [*pipeline.job_ids, *criados])
            await _purge_controlled(pg_session, pipeline.feed_ids)
        except Exception as exc:  # pragma: no cover - só alcançável se o teardown falhar
            print(f"AVISO: limpeza do teste falhou: {exc!r}")
        for client in pipeline._clients:
            await client.aclose()


async def _arq_job_ids(pool: ArqRedis) -> list[str]:
    """Ids de job PRESENTES no Redis, sem o prefixo da chave (``arq:job:``)."""
    keys = [key async for key in pool.scan_iter(match=f"{job_key_prefix}*")]
    return [
        (key.decode() if isinstance(key, bytes) else key)[len(job_key_prefix) :] for key in keys
    ]


# --- (a) + (b) + (c): persistência, autores e ordem commit -> despacho ---------


async def test_feed_persiste_artigos_autores_e_dispara_depois_do_commit(
    feed_pipeline: FeedPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prova (a), (b) e (c) num único ciclo real de ingestão.

    (a) Os dois artigos do feed estão no PostgreSQL depois do commit, lidos por
        conexão independente (o que a sessão do teste enxergaria mesmo sem commit).
    (b) Os autores vieram do ``dc:creator`` repetido e estão em ``article_authors``
        com ``position`` 0/1 e ``role='author'``, e em ``authors`` normalizados.
    (c) Os despachos (classificação dos dois artigos + download do PDF do artigo
        open access) acontecem DEPOIS do commit: no instante de cada chamada o
        artigo já é visível em outra conexão — a sonda falha se não for. Os jobs
        ficam no Redis REAL (``arq:job:<id>`` + membro de ``arq:queue``).
    """
    xml = _feed_xml(
        _item(
            guid="t15-guid-alfa",
            title="Artigo Controlado Alfa",
            link=f"https://{FEED_HOST}/artigo/alfa",
            creators=("T15 Autor Alfa", "T15 Autor Beta"),
        ),
        _item(
            guid="t15-guid-beta",
            title="Artigo Controlado Beta",
            link=f"https://{FEED_HOST}/artigo/beta",
            creators=("T15 Autor Gama",),
            extra=(
                "<dc:rights>open access</dc:rights>"
                f'<enclosure url="https://{FEED_HOST}/artigo/beta.pdf"'
                ' type="application/pdf" length="1234"/>'
            ),
        ),
    )
    feed = await feed_pipeline.create_feed(FEED_URL_ALFA, name="t15-feed-alfa")
    feed_pipeline.spy_dispatches_with_ordering(monkeypatch)
    service = feed_pipeline.build_service(feed.feed_url, xml)

    result = await service.sync_feed(feed.id)
    feed_id = feed.id

    assert result.success is True
    assert result.new_articles == 2
    assert result.errors == [], f"o feed controlado não deveria ter erro: {result.errors}"

    # (a) artigos persistidos, lidos por outra conexão.
    articles = await verifier.articles_of_feed(feed_id)
    assert [row.title for row in articles] == [
        "Artigo Controlado Alfa",
        "Artigo Controlado Beta",
    ], f"artigos persistidos: {articles}"
    alfa, beta = articles
    assert alfa.doi is None and beta.doi is None
    parser = ArticleParserService()
    assert {row.external_id for row in articles} == {
        parser.generate_external_id({"id": "t15-guid-alfa"}, feed_id),
        parser.generate_external_id({"id": "t15-guid-beta"}, feed_id),
    }, "o external_id persistido não é a chave feed_{id}_{md5(guid)} medida"

    # (b) autores associados com posição e papel.
    alfa_authors = await verifier.author_links(alfa.id)
    assert [(row.name, row.position, row.role) for row in alfa_authors] == [
        ("T15 Autor Alfa", 0, "author"),
        ("T15 Autor Beta", 1, "author"),
    ], f"autores associados ao artigo alfa: {alfa_authors}"
    beta_authors = await verifier.author_links(beta.id)
    assert [(row.name, row.position, row.role) for row in beta_authors] == [
        ("T15 Autor Gama", 0, "author"),
    ], f"autores associados ao artigo beta: {beta_authors}"
    assert all(row.normalized_name for row in alfa_authors + beta_authors)

    # (c) ordem commit -> despacho, medida dentro do fluxo.
    assert [entry.split(":")[0] for entry in feed_pipeline.trace] == [
        "classify",
        "classify",
        "download_pdf",
    ], f"trace de despacho inesperado: {feed_pipeline.trace}"
    assert all("visivel_em_outra_conexao=True" in entry for entry in feed_pipeline.trace), (
        f"algum despacho aconteceu antes do commit: {feed_pipeline.trace}"
    )
    assert [entry.split(":")[0] for entry in feed_pipeline.enqueued] == [
        "classify",
        "classify",
        "download_pdf",
    ], f"jobs realmente enfileirados: {feed_pipeline.enqueued}"
    assert len(feed_pipeline.job_ids) == 3

    # (c) os jobs estão no Redis REAL — e não no executor inline.
    await _assert_jobs_no_redis_real(arq_pool, feed_pipeline.job_ids)
    assert await arq_pool.zcard(default_queue_name) == 3

    # Nenhuma URL fora do mapa controlado foi pedida, ou seja: nenhuma tentativa
    # de internet externa (o MockTransport nunca abre socket).
    assert feed_pipeline.unexpected == [], (
        f"o pipeline pediu URLs fora do feed controlado: {feed_pipeline.unexpected}"
    )
    assert set(feed_pipeline.served) == {feed.feed_url}

    stats = await verifier.feed_stats(feed_id)
    assert (stats.error_count, stats.last_error) == (0, None)
    assert (stats.articles_last_sync, stats.total_articles) == (2, 2)


async def test_commit_que_falha_nao_dispara_job_nem_persiste_artigo(
    feed_pipeline: FeedPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O outro lado de (c): sem commit, nenhum job e nenhuma linha.

    A sonda é a mesma do teste anterior — ela falha se for chamada. O commit da
    sessão é trocado por um que levanta erro: o fluxo não pode despachar, o Redis
    não pode ganhar chave nenhuma e o artigo não pode existir para outra conexão.
    """

    async def _commit_falho() -> None:
        raise RuntimeError("falha de commit injetada pelo teste (T4.4)")

    xml = _feed_xml(
        _item(
            guid="t15-guid-sem-commit",
            title="Artigo Controlado Sem Commit",
            link=f"https://{FEED_HOST}/artigo/sem-commit",
            creators=("T15 Autor Zeta",),
        )
    )
    feed = await feed_pipeline.create_feed(FEED_URL_GAMA, name="t15-feed-gama")
    feed_pipeline.spy_dispatches_with_ordering(monkeypatch)
    service = feed_pipeline.build_service(feed.feed_url, xml)

    jobs_before = await _arq_job_ids(arq_pool)
    monkeypatch.setattr(feed_pipeline.session, "commit", _commit_falho)

    with pytest.raises(RuntimeError, match="falha de commit injetada"):
        await service.sync_feed(feed.id)

    assert feed_pipeline.trace == [], f"houve despacho com o commit falhando: {feed_pipeline.trace}"
    assert feed_pipeline.enqueued == []
    assert feed_pipeline.job_ids == []
    assert await _arq_job_ids(arq_pool) == jobs_before, (
        "o Redis ganhou chave de job apesar de o commit ter falhado"
    )
    assert await verifier.articles_of_feed(feed.id) == [], (
        "artigo visível em outra conexão sem commit"
    )


# --- (d) duplicata não gera novo artigo ----------------------------------------


async def test_duplicata_nao_gera_novo_artigo_nem_novo_job(
    feed_pipeline: FeedPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
) -> None:
    """Prova (d) e fixa a semântica da chave: a deduplicação é POR FEED.

    Medições deste teste:

    1. re-sincronizar o MESMO feed com o MESMO payload → ``new_articles == 0``,
       ``errors == []`` (a duplicata é reconhecida ANTES do INSERT: a chave
       ``feed_{id}_{md5(guid)}`` já existe) e NENHUM job novo no Redis. A asserção
       em ``errors`` é a que discrimina: um dedupe feito só pela violação de
       unique no INSERT também daria 0 artigos novos, mas com erro na entrada;
    2. o MESMO guid em OUTRO feed → 1 artigo NOVO (a chave carrega o ``feed_id``);
    3. o mesmo guid repetido duas vezes no payload → 1 artigo e nenhum erro.
    """
    guid_um = "t15-guid-repetido"
    guid_dois = "t15-guid-unico"
    xml = _feed_xml(
        _item(
            guid=guid_um,
            title="Artigo Controlado Repetido",
            link=f"https://{FEED_HOST}/artigo/repetido",
            creators=("T15 Autor Eta",),
        ),
        _item(
            guid=guid_dois,
            title="Artigo Controlado Unico",
            link=f"https://{FEED_HOST}/artigo/unico",
            creators=("T15 Autor Teta",),
        ),
    )
    feed_a = await feed_pipeline.create_feed(FEED_URL_ALFA, name="t15-feed-alfa")
    service_a = feed_pipeline.build_service(feed_a.feed_url, xml)

    first = await service_a.sync_feed(feed_a.id)
    assert first.success is True
    assert first.new_articles == 2
    assert first.errors == []

    ids_do_primeiro_sync = [row.id for row in await verifier.articles_of_feed(feed_a.id)]
    assert len(ids_do_primeiro_sync) == 2
    zcard_do_primeiro_sync = await arq_pool.zcard(default_queue_name)
    assert zcard_do_primeiro_sync == 2

    # (1) mesmo feed, mesmo payload: 0 novos, 0 erros, 0 jobs.
    second = await service_a.sync_feed(feed_a.id)
    assert second.success is True
    assert second.new_articles == 0, "o mesmo feed gerou artigo duplicado"
    assert second.errors == [], (
        "a duplicata foi detectada por ERRO (violação de unique no INSERT) em vez "
        f"da pré-checagem por external_id: {second.errors}"
    )
    assert [row.id for row in await verifier.articles_of_feed(feed_a.id)] == ids_do_primeiro_sync
    assert await arq_pool.zcard(default_queue_name) == zcard_do_primeiro_sync, (
        "a duplicata enfileirou job novo"
    )

    # (2) + (3) mesmo guid em outro feed (e duas vezes no payload): 1 artigo novo.
    xml_beta = _feed_xml(
        _item(
            guid=guid_um,
            title="Artigo Controlado Repetido em Outro Feed",
            link=f"https://{FEED_HOST}/artigo/repetido-outro-feed",
            creators=("T15 Autor Iota",),
            extra="<dc:identifier>10.1590/t15-outro-feed</dc:identifier>",
        ),
        _item(
            guid=guid_um,
            title="Artigo Controlado Repetido em Outro Feed",
            link=f"https://{FEED_HOST}/artigo/repetido-outro-feed",
            creators=("T15 Autor Iota",),
            extra="<dc:identifier>10.1590/t15-outro-feed</dc:identifier>",
        ),
    )
    feed_b = await feed_pipeline.create_feed(FEED_URL_BETA, name="t15-feed-beta")
    service_b = feed_pipeline.build_service(feed_b.feed_url, xml_beta)

    third = await service_b.sync_feed(feed_b.id)
    assert third.success is True
    assert third.new_articles == 1, (
        "o MESMO guid em outro feed deveria gerar 1 artigo novo (a chave de dedupe "
        f"carrega o feed_id) e o guid repetido no payload não pode duplicar: {third}"
    )
    assert third.errors == []
    assert await arq_pool.zcard(default_queue_name) == zcard_do_primeiro_sync + 1

    parser = ArticleParserService()
    chave_em_a = parser.generate_external_id({"id": guid_um}, feed_a.id)
    chave_em_b = parser.generate_external_id({"id": guid_um}, feed_b.id)
    assert chave_em_a != chave_em_b, "a chave de dedupe não é por feed"
    assert [row.external_id for row in await verifier.articles_of_feed(feed_b.id)] == [chave_em_b]


# --- (e) entrada inválida não aborta o feed inteiro ---------------------------


async def test_entrada_invalida_nao_aborta_o_feed(
    feed_pipeline: FeedPipeline,
    verifier: Verifier,
) -> None:
    """Prova (e): uma entrada inválida é isolada; as VÁLIDAS antes e depois ficam.

    A entrada inválida é inválida de verdade no banco: o DOI dela já existe
    (``articles.doi`` é único), então o ``flush`` daquela entrada viola a constraint.
    O caminho exercitado é o savepoint por entrada (``db.begin_nested()``) + o
    ``except`` da entrada (``app/services/feed_aggregator.py:190-209``): a transação
    do feed continua válida e o commit final persiste o resto. Sem o savepoint, a
    violação aborta a transação do feed inteiro — é o que a mutação prova.

    O feed termina ``success=True`` com ``errors`` de tamanho 1 e ``error_count=0``:
    a entrada ruim é registrada, não transformada em falha do feed.
    """
    xml = _feed_xml(
        _item(
            guid="t15-guid-antes",
            title="Artigo Controlado Antes da Invalida",
            link=f"https://{FEED_HOST}/artigo/antes",
            creators=("T15 Autor Kapa",),
        ),
        _item(
            guid="t15-guid-invalida",
            title="Artigo Controlado Invalido",
            # O DOI sai da própria URL (o parser o extrai do link) e colide com o
            # artigo-semente commitado abaixo.
            link=f"https://{FEED_HOST}/artigo/{DOI_COLIDENTE}",
            creators=("T15 Autor Lambda",),
        ),
        _item(
            guid="t15-guid-depois",
            title="Artigo Controlado Depois da Invalida",
            link=f"https://{FEED_HOST}/artigo/depois",
            creators=("T15 Autor Mi",),
        ),
    )
    seed_feed = await feed_pipeline.create_feed(FEED_URL_GAMA, name="t15-feed-gama-semente")
    seed = await feed_pipeline.seed_article_with_doi(seed_feed, DOI_COLIDENTE)
    feed = await feed_pipeline.create_feed(FEED_URL_DELTA, name="t15-feed-delta")
    service = feed_pipeline.build_service(feed.feed_url, xml)

    result = await service.sync_feed(feed.id)

    assert result.success is True, f"a entrada inválida derrubou o feed: {result}"
    assert result.new_articles == 2, f"artigos novos: {result}"
    assert len(result.errors) == 1, f"erros por entrada: {result.errors}"

    articles = await verifier.articles_of_feed(feed.id)
    assert [row.title for row in articles] == [
        "Artigo Controlado Antes da Invalida",
        "Artigo Controlado Depois da Invalida",
    ], (
        "as entradas válidas antes E depois da inválida têm de estar persistidas "
        f"(o feed foi abortado no meio): {articles}"
    )
    assert all(row.doi != DOI_COLIDENTE for row in articles), (
        "a entrada inválida virou artigo (DOI colidente persistido)"
    )
    # Os autores das duas entradas válidas chegaram junto.
    assert len(await verifier.author_links(articles[0].id)) == 1
    assert len(await verifier.author_links(articles[1].id)) == 1

    stats = await verifier.feed_stats(feed.id)
    assert stats.error_count == 0, (
        f"a entrada inválida marcou o feed como com erro: error_count={stats.error_count} "
        f"last_error={stats.last_error!r}"
    )
    assert stats.articles_last_sync == 2
    assert seed.id is not None, "o artigo-semente continua sendo o único com o DOI"


# --- ponta a ponta: feed -> DB -> Redis -> worker REAL -> DB -------------------


async def test_fluxo_ponta_a_ponta_feed_ate_worker_arq_real(
    feed_pipeline: FeedPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    pg_session: AsyncSession,
    run_arq_worker: RunArqWorker,
) -> None:
    """O teste ponta a ponta controlado da ingestão: o worker REAL classifica.

    Depois do ``sync_feed`` o Redis real tem exatamente os jobs de classificação
    do feed; um worker ARQ real (as ``functions``/hooks/limites de
    ``WorkerSettings``, ver ``tests/integration/conftest.py``) os executa e grava a
    classificação no PostgreSQL real. As asserções finais são sobre EFEITO no
    banco: ``classification_confidence``/``category_id`` preenchidos e o vínculo em
    ``article_categories``. Nenhum artigo deste payload é open access, então não há
    job de download de PDF — o worker não tenta rede nenhuma.

    Antes de rodar o worker, a fila é conferida (``zcard``) para garantir que só os
    jobs deste teste estão em voo: um job de PDF de outro teste sendo executado aqui
    faria o worker tentar baixar de verdade.
    """
    xml = _feed_xml(
        _item(
            guid="t15-guid-e2e-um",
            title="Artigo Controlado E2E Um",
            link=f"https://{FEED_HOST}/artigo/e2e-um",
            creators=("T15 Autor Ni",),
        ),
        _item(
            guid="t15-guid-e2e-dois",
            title="Artigo Controlado E2E Dois",
            link=f"https://{FEED_HOST}/artigo/e2e-dois",
            creators=("T15 Autor Xi",),
        ),
    )
    # Categorias padrão semeadas pelo helper de produção: dois jobs em voo no mesmo
    # worker não podem disputar a CRIAÇÃO da categoria (a corrida do vínculo já tem
    # teste próprio no 14.B) — aqui o alvo é a ingestão.
    for category in DEFAULT_CATEGORIES:
        await ClassificationService.get_or_create_category(
            pg_session,
            slug=category["slug"],
            name=category["name"],
            description=category["description"],
        )
    await pg_session.commit()

    feed = await feed_pipeline.create_feed(FEED_URL_DELTA, name="t15-feed-delta-e2e")
    service = feed_pipeline.build_service(feed.feed_url, xml)

    jobs_before = set(await _arq_job_ids(arq_pool))
    result = await service.sync_feed(feed.id)
    feed_id = feed.id

    assert result.success is True
    assert result.new_articles == 2
    assert result.errors == []

    job_ids = sorted(set(await _arq_job_ids(arq_pool)) - jobs_before)
    feed_pipeline.job_ids.extend(job_ids)
    assert len(job_ids) == 2, f"jobs de classificação enfileirados: {job_ids}"
    await _assert_jobs_no_redis_real(arq_pool, job_ids)
    assert await arq_pool.zcard(default_queue_name) == 2, (
        "há job de outro teste na fila: o worker real poderia executar um download "
        "de PDF e sair para a rede"
    )

    worker = await run_arq_worker()

    assert worker.jobs_failed == 0, (
        f"o worker real falhou (jobs_complete={worker.jobs_complete} "
        f"jobs_failed={worker.jobs_failed} jobs_retried={worker.jobs_retried})"
    )
    assert worker.jobs_complete == 2
    for job_id in job_ids:
        info = await Job(job_id, arq_pool).result_info()
        assert info is not None, f"nenhum resultado em arq:result:{job_id}"
        assert info.success is True, f"resultado real do job: {info!r}"

    rows = await verifier.articles_of_feed(feed_id)
    assert len(rows) == 2
    for row in rows:
        assert row.classification_confidence is not None, (
            f"o worker real não classificou o artigo {row.id}: {row}"
        )
        assert row.category_id is not None
        links = await verifier.category_links(row.id)
        assert len(links) == 1, f"vínculo artigo↔categoria do artigo {row.id}: {links}"
        assert links[0].category_id == row.category_id

    stats = await verifier.feed_stats(feed_id)
    assert stats.articles_last_sync == 2


# --- falso-verde: a guarda de Redis real rejeita o caminho inline --------------


async def test_guarda_de_chaves_no_redis_rejeita_o_caminho_inline(
    feed_pipeline: FeedPipeline,
    arq_pool: ArqRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prova que a guarda da suíte NÃO passa pelo caminho inline de ``ENABLE_ARQ``.

    ``settings.enable_arq`` é ``False`` por default (``app/config.py:63``) e, nesse
    estado, ``get_task_queue()`` devolve ``InlineTaskQueue`` sem avisar: o trabalho
    roda como ``asyncio.Task`` local e o Redis fica vazio. Um teste que only
    assertasse "o dispatch retornou um id" ficaria verde provando nada sobre
    produção — por isso toda asserção de despacho passa por
    ``_assert_jobs_no_redis_real``.

    Aqui estão os dois controles: um job REAL passa pela guarda (positivo) e um job
    no formato do executor inline é REJEITADO por ela (negativo). O próprio nome do
    job inline é derivado da classe que ``ENABLE_ARQ=false`` seleciona — se o
    dispatcher passar a enfileirar no Redis com ``ENABLE_ARQ=false``, ou se a guarda
    for afrouxada, este teste falha.
    """
    # Controle POSITIVO: um despacho pelo caminho de produção passa na guarda.
    job_id = await real_dispatch_classify_article(2**31 - 1)
    feed_pipeline.job_ids.append(job_id)
    await _assert_jobs_no_redis_real(arq_pool, [job_id])
    assert not job_id.startswith(INLINE_JOB_ID_HINT)

    # Controle NEGATIVO: com ENABLE_ARQ=false a fila é a inline…
    monkeypatch.setattr(settings, "enable_arq", False)
    task_dispatcher._inline_queue = None
    queue = task_dispatcher.get_task_queue()
    assert isinstance(queue, InlineTaskQueue), (
        f"com ENABLE_ARQ=false a fila tem de ser a inline, veio {type(queue)!r}"
    )
    assert not isinstance(queue, ArqTaskQueue)

    # …e o job que ela produziria NÃO tem chave nenhuma no Redis real.
    inline_job_id = f"{INLINE_JOB_ID_HINT}classify-{2**31 - 1}"
    assert await arq_pool.exists(f"{job_key_prefix}{inline_job_id}") == 0
    with pytest.raises(AssertionError) as excinfo:
        await _assert_jobs_no_redis_real(arq_pool, [inline_job_id])
    assert INLINE_JOB_ID_HINT in str(excinfo.value)
