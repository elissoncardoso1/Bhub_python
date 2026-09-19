"""Article OA -> job ARQ real -> download -> extracao -> persistencia (Task 16 / T4.5).

O épico 4 do plano (``docs/superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md``,
seção "Task 16", linha 1141) pede o fluxo PDF determinístico:

    article OA -> job -> download fixture -> extract -> persist

e sete critérios de aceite literais, todos cobertos aqui: PostgreSQL REAL, Redis REAL,
``alembic upgrade head`` já aplicado (fixture ``migrated_database``), TSVector validado na
suíte irmã ``test_postgres_search.py``, ARQ validado ALÉM de mocks (worker de produção em
modo ``burst``), pelo menos um fluxo de ingestão ponta a ponta controlado, e nenhuma
dependência de internet externa. A regra literal do épico — *"Evitar rede pública em CI.
Servir fixture local ou mockar apenas a fronteira HTTP."* — é cumprida pelo caminho mais
estreito possível: **a ÚNICA costura falsa desta suíte é o transporte HTTP**
(``httpx.MockTransport``), que não abre socket nenhum. Download, leitura de bytes, validação
de magic bytes, extração com PyMuPDF/pdfplumber, gravação em disco, cálculo de hash e a
persistência transacional em ``articles`` + ``pdf_metadata`` são código de PRODUÇÃO rodando
de verdade contra os containers dos fixtures.

Por que o fixture de PDF é gerado em processo
---------------------------------------------

O repositório não tem nenhum arquivo ``.pdf`` nem ``reportlab``/``fpdf`` como dependência,
então o fixture é construído com o MESMO PyMuPDF que a produção usa para ler
(``app/services/pdf_service.py``). Isso não é detalhe de conveniência: é o que torna a
suíte *determinística* de verdade.

**Fato medido, e o motivo da suite existir como existe:** ``doc.tobytes()`` NÃO é estável
byte a byte — o ``/ID`` do trailer muda a cada construção (10 construções independentes
produziram 10 sha256 distintos; dois builds diferiram em dezenas de bytes).
``doc.tobytes(no_new_id=1, deflate=True)`` É estável: 10 construções independentes
produziram 1 único sha256. O parâmetro ``reproducible=1`` sozinho NÃO estabiliza os bytes.
Por isso ``_build_pdf`` usa ``no_new_id=1, deflate=True`` e
``test_determinismo_do_fixture_e_do_pipeline`` constrói o fixture duas vezes e compara o
sha256 — a asserção que dá sentido à palavra "determinístico" no título da task.

O que esta suíte PINa: comportamento ATUAL, não desejado
-------------------------------------------------------

As asserções abaixo prendem o contrato MEDIDO contra o PostgreSQL real, inclusive onde ele
é ambíguo. Nenhuma linha de ``app/`` foi mudada para fabricar verde.

1. **Sucesso**: o job devolve ``status == "processed"`` (``app/jobs/tasks.py:80-86``) e
   grava ``articles.pdf_file_path``/``pdf_file_size`` (``pdf_service.py:459-460``) e a linha
   de ``pdf_metadata`` com ``processing_status=COMPLETED`` e ``extracted_text`` preenchido
   (``pdf_service.py:462-487``).
2. **Falha de download/extração vira ``skipped``, não ``FAILED``.** HTTP 404/500, timeout,
   payload não-PDF e ``%PDF`` corrompido são TODOS engolidos em
   ``pdf_service.py:632-639`` (``except httpx.TimeoutException`` / ``httpx.HTTPStatusError``
   / ``Exception`` -> ``return None``); ``process_article_pdf`` devolve ``None`` e o job
   devolve ``{"status": "skipped"}`` (``app/jobs/tasks.py:74-75``). Nenhuma linha de
   ``pdf_metadata`` é criada, nenhum ``FAILED`` aparece e o job NÃO morre
   (``jobs_failed == 0``; não há ``raise`` no caminho, então o ``retry_jobs`` do worker nem
   é acionado). O status ``ProcessingStatus.FAILED`` (``app/models/pdf_metadata.py:19``) é,
   hoje, **código morto** — este caminho do pipeline nunca o alcança.
3. **OBSERVAÇÃO registrada, não corrigida**: ``skipped`` é ambíguo — ele conflita dois
   mundos que a operação precisa distinguir: "não havia trabalho a fazer" (artigo já tem
   PDF, não é open access, sem URL, duplicata por hash) e "o trabalho falhou" (404/500/
   timeout/payload inválido). Um alerta sobre ``skipped`` hoje é inútil como sinal de saúde
   do pipeline. O contrato literal desta task não exige distinguir os dois casos, então a
   suíte prende o comportamento como ele é e registra a observação para o ledger — não a
   conserta aqui.
4. **``skipped`` depois de baixar é diferente de ``skipped`` antes de chamar HTTP.** Os dois
   casos estão separados em testes distintos de propósito, porque a diferença é observável
   na contagem de requisições: artigo que já tem PDF retorna ANTES do HTTP (zero chamadas ao
   handler), enquanto a duplicata por hash só é descoberta DEPOIS do download (uma chamada
   ao handler, arquivo órfão removido do disco).
5. **OBSERVAÇÃO registrada, não corrigida — corrida entre jobs concorrentes**: dois jobs de
   PDF com os MESMOS bytes rodando no mesmo worker ``burst`` (até ``max_jobs=10`` jobs
   concorrentes) passam AMBOS pela pré-checagem ``check_duplicate`` antes de qualquer commit
   (TOCTOU) e o perdedor da corrida estoura ``UniqueViolationError`` em
   ``pdf_metadata_file_hash_key`` — medido, ``jobs_failed=1``, com o arquivo órfão removido
   pelo rollback. Qual job perde depende do escalonamento, então **não é determinístico e
   não é prensado por teste nenhum**; a única garantia real de unicidade hoje é a constraint
   do banco, não a pré-checagem. O teste de duplicata desta suíte roda os dois jobs em duas
   execuções SEQUENCIAIS justamente para medir o caminho determinístico.

Como "sem internet externa" é provado, e não presumido
------------------------------------------------------

O ``MockTransport`` é o único transporte do serviço: ``PDFService(upload_path=...,
http_client=...)`` tem precedência sobre o client efêmero (``pdf_service.py:576-586``), logo
não existe caminho que crie ``httpx.AsyncClient`` real. Além disso, cada teste confere o
livro-caixa do handler: ``served`` (URLs servidas) tem de ser EXATAMENTE o conjunto
esperado e ``unexpected`` (URLs fora do mapa controlado) tem de estar vazio. Host fora do
DNS, requisição a outro host e payload faltando aparecem como ``unexpected``, não como
timeout de rede silencioso. O worker é criado com um ``WorkerSettings`` local
(``_pdf_only_worker_settings``) cujo ``on_startup`` injeta ``ctx["pdf_service"]`` — o mesmo
seam de ``ctx["pdf_service"]`` de produção (``app/jobs/tasks.py:64-65``) — e que substitui
APENAS o ``startup`` de produção (o qual carrega o MiniLM e, com
``settings.enable_telemetry``, telemetria). Limites (``max_jobs``/``job_timeout``/
``max_tries``/``retry_jobs``/``keep_result``), hooks (``on_job_start``/``on_job_end``/
``on_shutdown``) e o dispatcher continuam sendo os de produção.

Isolamento
----------

Cada teste cria os SEUS artigos (``external_id`` prefixado com ``t16-``), usa o SEU
``tmp_path`` como storage (nunca o ``settings.pdf_upload_path`` de produção, que gravaria
dentro do repositório) e limpa as suas linhas, arquivos e chaves ARQ no teardown. Antes de
rodar o worker, a fila é conferida (``zcard`` + membros): um job de PDF de outra suíte
sendo drenado aqui faria o worker tentar baixar de verdade da internet.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import fitz
import httpx
import pytest
import pytest_asyncio
from arq.connections import ArqRedis
from arq.constants import default_queue_name, job_key_prefix, result_key_prefix
from arq.jobs import Job
from sqlalchemy import Row, delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.jobs.tasks import WorkerSettings, task_download_pdf
from app.models import Article, PDFMetadata, ProcessingStatus, SourceType
from app.services.pdf_service import PDFService
from app.services.task_dispatcher import dispatch_download_pdf
from tests.integration.conftest import RunArqWorker

pytestmark = pytest.mark.integration

#: Host das URLs controladas. NÃO é resolvido por DNS: o único transporte desta suíte é o
#: ``httpx.MockTransport`` injetado em ``PDFService(http_client=...)``.
PDF_HOST = "mock16.local"

#: Prefixo de todo artigo criado por esta suíte (usado na limpeza e nas asserções).
EXTERNAL_ID_PREFIX = "t16-"

#: Job id do caminho inline (``ENABLE_ARQ=false``): ``inline-pdf-<id>``. Se algum job desta
#: suíte tiver esse prefixo, o trabalho NÃO passou pelo Redis/ARQ real.
INLINE_JOB_ID_HINT = "inline-"

# --- Fixture de PDF determinístico --------------------------------------------


def _build_pdf(lines: Sequence[str]) -> bytes:
    """PDF de uma página, gerado em processo e **byte-estável**.

    ``no_new_id=1`` congela o ``/ID`` do trailer e ``deflate=True`` fixa a compressão dos
    streams: medido, 10 construções independentes produzem UM único sha256 (com
    ``tobytes()`` puro são 10 sha256 distintos). Linhas vazias são descartadas de
    propósito: o PyMuPDF não emite nada para elas e a comparação literal de texto extraído
    ficaria dependente desse detalhe.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 em pontos
    y = 72.0
    try:
        for line in lines:
            if not line:
                continue
            page.insert_text((72, y), line, fontsize=12)
            y += 18.0
        return doc.tobytes(no_new_id=1, deflate=True)
    finally:
        doc.close()


#: Linhas de cada fixture controlado. Os dois conjuntos diferem só pelo marcador
#: (``Alfa``/``Beta``) para que os bytes — e portanto o ``file_hash`` — sejam diferentes:
#: dois artigos servidos com bytes IDÊNTICOS colidiriam com a deduplicação por hash
#: (``pdf_service.check_duplicate``), que é um caso de teste próprio.
_LINES_ALFA: tuple[str, ...] = (
    "T16 Deterministic PDF Fixture Alfa",
    "Article OA to ARQ job to download to extract to persist",
    "Abstract",
    "Alfa marker line for the deterministic pipeline suite",
)

_LINES_BETA: tuple[str, ...] = (
    "T16 Deterministic PDF Fixture Beta",
    "Article OA to ARQ job to download to extract to persist",
    "Abstract",
    "Beta marker line for the deterministic pipeline suite",
)


def _extract_with_pymupdf(data: bytes) -> str:
    """O que a PRODUÇÃO extrai desses bytes (``PDFService._extract_text`` via PyMuPDF)."""
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _expected_filename(title: str) -> str:
    """Mesma sanitização de ``PDFService.process_pdf`` (``re.sub(r"[^\\w\\-.]", "_", ...)``)."""
    safe_title = re.sub(r"[^\w\-.]", "_", title[:100])
    return f"{safe_title}.pdf"


# --- Guias anti-falso-verde (testados em test_guarda_* abaixo) -----------------


def _assert_only_expected_urls(
    served: Sequence[str], unexpected: Sequence[str], expected: Sequence[str]
) -> None:
    """Guarda de TODO teste desta suíte: nada além do mapa controlado foi pedido.

    Falha tanto quando uma URL fora do mapa foi pedida (``unexpected``) quanto quando o
    conjunto servido não é EXATAMENTE o esperado. Sem ela, um teste poderia ficar verde
    tendo aberto conexão para outro host. ``test_guarda_de_urls_fora_do_mapa_e_detectada``
    prova que a guarda REJEITA uma URL intrusa — ela não é decorativa.
    """
    assert list(unexpected) == [], (
        f"o pipeline pediu URLs fora do mapa controlado desta suíte: {list(unexpected)}"
    )
    assert sorted(served) == sorted(expected), (
        f"URLs servidas {sorted(served)} diferentes das esperadas {sorted(expected)}"
    )


async def _queue_members(pool: ArqRedis) -> list[str]:
    """Membros do zset ``arq:queue`` (o que um worker ``burst`` drenaria), em ordem."""
    members = await pool.zrange(default_queue_name, 0, -1)
    return [m.decode() if isinstance(m, bytes) else m for m in members]


async def _assert_queue_only(pool: ArqRedis, expected_job_ids: Sequence[str]) -> None:
    """A fila tem de conter SOMENTE os jobs deste teste antes de o worker rodar.

    Um job de PDF deixado por OUTRA suíte seria drenado pelo worker daqui e faria o
    ``task_download_pdf`` sair para a rede de verdade — exatamente o que a regra
    "evitar rede pública" proíbe. ``test_guarda_da_fila_rejeita_job_intruso`` prova que
    esta guarda REJEITA um intruso.
    """
    members = await _queue_members(pool)
    assert set(members) == set(expected_job_ids), (
        f"a fila real tem jobs que não são deste teste: {members} (esperado "
        f"{list(expected_job_ids)}) — o worker poderia executá-los e sair para a rede"
    )
    assert await pool.zcard(default_queue_name) == len(expected_job_ids)


async def _arq_job_ids(pool: ArqRedis) -> list[str]:
    """Ids de job PRESENTES no Redis, sem o prefixo da chave (``arq:job:``)."""
    keys = [key async for key in pool.scan_iter(match=f"{job_key_prefix}*")]
    return [
        (key.decode() if isinstance(key, bytes) else key)[len(job_key_prefix) :] for key in keys
    ]


async def _drop_arq_keys(pool: ArqRedis, job_ids: Sequence[str]) -> None:
    """Remove da fila e do Redis os jobs controlados por esta suíte."""
    for job_id in job_ids:
        await pool.zrem(default_queue_name, job_id)
        await pool.delete(f"{job_key_prefix}{job_id}")
        await pool.delete(f"{result_key_prefix}{job_id}")


# --- Conexão INDEPENDENTE para ler o que foi commitado -------------------------


class Verifier:
    """Engine próprio (``NullPool``) para ler o banco por FORA da sessão do teste.

    A sessão do teste tem transação e cache de identidade do ORM, e o job ARQ escreve numa
    sessão DIFERENTE (``ctx["db"]``, criada por ``session_factory`` dentro do worker).
    Ler o resultado pelas mesmas estruturas do teste confundiria "commitado pelo worker"
    com "pendente no meu unit of work". Cada leitura aqui abre conexão nova e só enxerga
    dado COMMITADO.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _rows(self, statement: Any) -> list[Any]:
        async with self._engine.connect() as conn:
            result = await conn.execute(statement)
            return list(result.all())

    async def article_pdf_columns(self, article_id: int) -> Row[Any] | None:
        """``(pdf_file_path, pdf_file_size, is_open_access)`` do artigo, ou None."""
        rows = await self._rows(
            select(Article.pdf_file_path, Article.pdf_file_size, Article.is_open_access).where(
                Article.id == article_id
            )
        )
        return rows[0] if rows else None

    async def pdf_metadata(self, article_id: int) -> Row[Any] | None:
        """``(file_hash, original_filename, page_count, word_count, extracted_text, status)``."""
        rows = await self._rows(
            select(
                PDFMetadata.file_hash,
                PDFMetadata.original_filename,
                PDFMetadata.page_count,
                PDFMetadata.word_count,
                PDFMetadata.extracted_text,
                PDFMetadata.processing_status,
            ).where(PDFMetadata.article_id == article_id)
        )
        return rows[0] if rows else None

    async def rows_with_hash(self, file_hash: str) -> list[Row[Any]]:
        """``(article_id, file_hash)`` de TODAS as linhas com esse hash (dedupe é único)."""
        return await self._rows(
            select(PDFMetadata.article_id, PDFMetadata.file_hash).where(
                PDFMetadata.file_hash == file_hash
            )
        )


@pytest_asyncio.fixture
async def verifier(migrated_database: str) -> AsyncGenerator[Verifier, None]:
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield Verifier(engine)
    finally:
        await engine.dispose()


# --- Worker ARQ real, com APENAS o pdf_service injetado ------------------------


def _pdf_only_worker_settings(pdf_service: PDFService) -> type[WorkerSettings]:
    """``WorkerSettings`` de produção com uma única costura: ``ctx["pdf_service"]``.

    O ``on_startup`` é substituído por um que só injeta o serviço no contexto — o mesmo
    seam que a produção expõe em ``app/jobs/tasks.py:64-65``. O ``startup`` de produção
    carrega o MiniLM (modelo de embeddings, dependência de rede/HF-hub e segundos de
    custo) e, se ``settings.enable_telemetry`` estivesse ligado, telemetria OTLP: nada
    disso pertence ao fluxo de PDF, e puxá-lo aqui quebraria o critério "sem internet
    externa". Tudo o mais continua sendo produção: ``functions``, ``max_jobs``,
    ``job_timeout``, ``max_tries``, ``retry_jobs``, ``keep_result`` e os hooks
    ``on_job_start``/``on_job_end``/``on_shutdown`` (é o ``on_job_start`` de produção que
    cria ``ctx["db"]`` a partir de ``ctx["session_factory"]``, apontado pelo fixture para o
    banco migrado do container).
    """

    class _PDFOnlyWorkerSettings(WorkerSettings):
        functions = [task_download_pdf]

        @staticmethod
        async def on_startup(ctx: dict[str, Any]) -> None:
            ctx["pdf_service"] = pdf_service

    return _PDFOnlyWorkerSettings


# --- Estado de UM teste --------------------------------------------------------


@dataclass(frozen=True)
class _Route:
    """Resposta controlada de UMA URL do mapa.

    ``timeout=True`` faz o handler LEVANTAR ``httpx.ReadTimeout`` (o mesmo tipo que o
    client real levanta ao estourar o prazo), exercitando o ``except
    httpx.TimeoutException`` de ``pdf_service.py:632`` pelo caminho real do httpx.
    """

    body: bytes = b""
    status_code: int = 200
    content_type: str = "application/pdf"
    timeout: bool = False


class PDFPipeline:
    """Sessão, "servidor" HTTP em memória, rastro de requisições e limpeza de UM teste."""

    def __init__(self, session: AsyncSession, verifier: Verifier, upload_path: Path) -> None:
        self.session = session
        self.verifier = verifier
        self.upload_path = upload_path
        self.routes: dict[str, _Route] = {}
        self.served: list[str] = []
        self.unexpected: list[str] = []
        self.handler_calls = 0
        self.article_ids: list[int] = []
        self.job_ids: list[str] = []
        self.file_paths: list[str] = []
        self._clients: list[httpx.AsyncClient] = []

    # -- "servidor" HTTP em memória ------------------------------------------

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.handler_calls += 1
        url = str(request.url)
        route = self.routes.get(url)
        if route is None:
            self.unexpected.append(url)
            return httpx.Response(404, text="URL fora do mapa controlado desta suíte")
        self.served.append(url)
        if route.timeout:
            raise httpx.ReadTimeout("timeout controlado da suíte T16", request=request)
        return httpx.Response(
            route.status_code,
            content=route.body,
            headers={"content-type": route.content_type},
        )

    def serve(self, url: str, route: _Route) -> str:
        self.routes[url] = route
        return url

    def serve_pdf(self, url: str, data: bytes) -> str:
        return self.serve(url, _Route(body=data, content_type="application/pdf"))

    def build_service(self) -> PDFService:
        """``PDFService`` REAL com o transporte HTTP trocado por ``MockTransport``.

        O ``upload_path`` é o ``tmp_path`` do teste de propósito: o default
        (``settings.pdf_upload_path``) gravaria dentro do repositório.
        """
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(self._handler),
            timeout=5.0,
            follow_redirects=True,
        )
        self._clients.append(client)
        return PDFService(upload_path=self.upload_path, http_client=client)

    # -- banco ---------------------------------------------------------------

    async def create_article(
        self,
        *,
        marker: str,
        pdf_url: str | None,
        pdf_file_path: str | None = None,
    ) -> Article:
        """Artigo open access controlado, COMMITADO antes de qualquer despacho."""
        article = Article(
            external_id=f"{EXTERNAL_ID_PREFIX}{marker}-{uuid.uuid4().hex[:8]}",
            title=f"T16 Artigo {marker}",
            abstract=f"Artigo controlado da suíte T16 ({marker}).",
            language="pt",
            original_url=f"https://{PDF_HOST}/artigo/{marker}",
            pdf_url=pdf_url,
            is_open_access=True,
            source_type=SourceType.RSS,
            publication_date=datetime(2026, 6, 1, tzinfo=UTC),
        )
        if pdf_file_path is not None:
            article.pdf_file_path = pdf_file_path
        self.session.add(article)
        await self.session.commit()
        assert article.id is not None, "o artigo controlado não recebeu id"
        self.article_ids.append(article.id)
        return article

    # -- observação do domínio -----------------------------------------------

    def files_on_disk(self) -> list[Path]:
        """Todo ``.pdf`` sob o storage do teste (o default de produção nunca é usado)."""
        if not self.upload_path.exists():
            return []
        return sorted(p for p in self.upload_path.rglob("*.pdf") if p.is_file())


async def _purge_controlled(session: AsyncSession, article_ids: Sequence[int]) -> None:
    """Apaga SÓ as linhas desta suíte: ``pdf_metadata`` dos meus artigos, depois artigos."""
    await session.rollback()
    if article_ids:
        await session.execute(
            delete(PDFMetadata)
            .where(PDFMetadata.article_id.in_(article_ids))
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(Article)
            .where(Article.id.in_(article_ids))
            .execution_options(synchronize_session=False)
        )
    await session.commit()


@pytest_asyncio.fixture
async def pdf_pipeline(
    pg_session: AsyncSession,
    verifier: Verifier,
    arq_pool: ArqRedis,
    tmp_path: Path,
) -> AsyncGenerator[PDFPipeline, None]:
    """Pipeline controlado com storage no ``tmp_path`` do teste.

    ``arq_pool`` é dependência explícita porque é ele quem liga ``ENABLE_ARQ`` e aponta o
    dispatcher para o Redis do container: sem isso o despacho cairia no executor INLINE em
    silêncio e o Redis ficaria vazio (o teste continuaria verde, provando nada).
    """
    pipeline = PDFPipeline(pg_session, verifier, tmp_path / "uploads" / "pdfs")
    jobs_at_start = set(await _arq_job_ids(arq_pool))
    try:
        yield pipeline
    finally:
        try:
            criados = sorted(set(await _arq_job_ids(arq_pool)) - jobs_at_start)
            await _drop_arq_keys(arq_pool, [*pipeline.job_ids, *criados])
            for path in pipeline.file_paths:
                Path(path).unlink(missing_ok=True)
            await _purge_controlled(pg_session, pipeline.article_ids)
        except Exception as exc:  # pragma: no cover - só alcançável se o teardown falhar
            print(f"AVISO: limpeza do teste falhou: {exc!r}")
        for client in pipeline._clients:
            await client.aclose()


async def _dispatch_and_run(
    pipeline: PDFPipeline,
    arq_pool: ArqRedis,
    run_arq_worker: RunArqWorker,
    articles: Sequence[Article],
) -> tuple[list[str], Any]:
    """Despacha um job por artigo, confere a fila e roda o worker REAL (``burst``).

    Devolve ``(job_ids, worker)`` com apenas os ids despachados NESTA chamada. As guardas
    são deliberadamente barulhentas: job id do caminho inline, chave de job ausente no
    Redis ou fila com job alheio reprovam o teste ANTES de o worker rodar.
    """
    dispatched: list[str] = []
    for article in articles:
        job_id = await dispatch_download_pdf(article.id)
        assert not job_id.startswith(INLINE_JOB_ID_HINT), (
            f"job id {job_id!r} é do caminho inline (ENABLE_ARQ=false): o trabalho NÃO "
            "passou pelo Redis/ARQ real"
        )
        assert await arq_pool.exists(f"{job_key_prefix}{job_id}") == 1, (
            f"chave arq:job:{job_id} ausente: o despacho não chegou ao Redis real"
        )
        dispatched.append(job_id)
        pipeline.job_ids.append(job_id)

    await _assert_queue_only(arq_pool, dispatched)
    worker = await run_arq_worker(settings=_pdf_only_worker_settings(pipeline.build_service()))
    return dispatched, worker


async def _job_result(arq_pool: ArqRedis, job_id: str) -> dict[str, Any]:
    """Resultado REAL do job, lido de ``arq:result:<id>``."""
    info = await Job(job_id, arq_pool).result_info()
    assert info is not None, f"nenhum resultado em arq:result:{job_id} (o job não rodou?)"
    assert info.success is True, f"o job terminou com erro: {info!r}"
    assert isinstance(info.result, dict), f"resultado do job não é dict: {info.result!r}"
    return info.result


# --- (1) ponta a ponta: artigo OA -> job -> download -> extract -> persist ------


async def test_fluxo_ponta_a_ponta_pdf_ate_worker_arq_real(
    pdf_pipeline: PDFPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    run_arq_worker: RunArqWorker,
) -> None:
    """O fluxo da task, ponta a ponta, com extração e persistência REAIS.

    Medições deste teste:

    1. o job foi despachado pelo dispatcher de produção e está no Redis REAL;
    2. o worker ARQ real (``burst``) executou exatamente 1 job e nenhum falhou;
    3. a ÚNICA chamada HTTP foi para a URL controlada (``served == [url]``,
       ``unexpected == []``) — nenhum outro host foi tentado;
    4. o arquivo em disco está sob o ``upload_path`` do teste e o conteúdo é
       byte a byte o que o "servidor" serviu;
    5. ``articles.pdf_file_path``/``pdf_file_size`` apontam para ele, lidos por
       conexão INDEPENDENTE (o worker commitou em outra sessão);
    6. a linha de ``pdf_metadata`` tem ``file_hash`` = sha256 dos bytes servidos,
       ``page_count``/``word_count``/``extracted_text`` da extração REAL e
       ``processing_status == COMPLETED``.
    """
    data = _build_pdf(_LINES_ALFA)
    expected_text = _extract_with_pymupdf(data)
    url = pdf_pipeline.serve_pdf(f"https://{PDF_HOST}/artigo/alfa.pdf", data)
    article = await pdf_pipeline.create_article(marker="Ponta a Ponta", pdf_url=url)

    assert await arq_pool.zcard(default_queue_name) == 0, (
        "a fila não está vazia ANTES deste teste: há job de outra suíte a ser drenado"
    )

    job_ids, worker = await _dispatch_and_run(pdf_pipeline, arq_pool, run_arq_worker, [article])
    assert worker.jobs_complete == 1, (
        f"o worker real não completou 1 job (complete={worker.jobs_complete} "
        f"failed={worker.jobs_failed} retried={worker.jobs_retried})"
    )
    assert worker.jobs_failed == 0, f"o job de PDF real falhou: {worker.jobs_failed}"

    result = await _job_result(arq_pool, job_ids[0])
    assert result["status"] == "processed", f"resultado do job: {result}"
    assert result["article_id"] == article.id

    # (3) livro-caixa da fronteira HTTP.
    _assert_only_expected_urls(pdf_pipeline.served, pdf_pipeline.unexpected, [url])
    assert pdf_pipeline.handler_calls == 1

    # (4) artefato em disco, byte a byte igual ao servido.
    path = Path(result["file_path"])
    assert path.is_file(), f"o PDF não foi gravado em disco: {path}"
    assert path.read_bytes() == data, "o arquivo gravado difere dos bytes servidos"
    assert str(path.resolve()).startswith(str(pdf_pipeline.upload_path.resolve())), (
        f"o PDF foi gravado fora do storage do teste: {path}"
    )
    pdf_pipeline.file_paths.append(str(path))

    # (5) colunas do artigo lidas por conexão INDEPENDENTE.
    columns = await verifier.article_pdf_columns(article.id)
    assert columns is not None, "o artigo controlado não existe no banco migrado"
    assert columns.pdf_file_path == str(path)
    assert columns.pdf_file_size == len(data)
    assert columns.is_open_access is True

    # (6) linha de pdf_metadata, com os valores MEDIDOS da extração real.
    meta = await verifier.pdf_metadata(article.id)
    assert meta is not None, "nenhuma linha de pdf_metadata foi persistida"
    assert meta.file_hash == _sha256(data), (
        "o file_hash persistido não é o sha256 dos bytes servidos"
    )
    assert meta.processing_status == ProcessingStatus.COMPLETED
    assert meta.page_count == 1
    assert meta.word_count == len(expected_text.split())
    assert meta.extracted_text == expected_text, (
        f"texto extraído inesperado:\n{meta.extracted_text!r}\n!=\n{expected_text!r}"
    )
    assert meta.original_filename == _expected_filename(article.title)
    assert [row.article_id for row in await verifier.rows_with_hash(meta.file_hash)] == [article.id]


# --- (2) determinismo, provado --------------------------------------------------


async def test_determinismo_do_fixture_e_do_pipeline(
    pdf_pipeline: PDFPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    run_arq_worker: RunArqWorker,
) -> None:
    """Determinismo em dois níveis: o FIXTURE e o PIPELINE.

    Nível 1 (é o que dá sentido à palavra "determinístico" no título da task): construir o
    mesmo fixture duas vezes produz sha256 IDÊNTICO. Medido: com
    ``tobytes(no_new_id=1, deflate=True)`` são 1 hash para N construções; com
    ``tobytes()`` puro são N hashes distintos (o ``/ID`` do trailer muda). O mesmo vale
    para os dois fixtures usados aqui.

    Nível 2: o pipeline é função APENAS dos bytes servidos. Dois artigos distintos, cada um
    com o seu fixture, em DUAS execuções completas (um único worker ``burst`` drenando os
    dois jobs) produzem a MESMA semântica — mesmo ``page_count``, mesmo
    ``processing_status``, e, para cada artigo, ``file_hash``/``word_count``/
    ``extracted_text`` exatamente iguais aos derivados dos bytes que aquele artigo recebeu.
    Os fixtures diferem de propósito no marcador (``Alfa``/``Beta``): bytes idênticos para
    dois artigos colidiriam na deduplicação por hash (teste próprio) e o segundo job
    voltaria ``skipped`` sem exercitar a persistência.

    Nota honesta de escopo: "mesmos bytes duas vezes pelo pipeline inteiro" é
    INOBSERVÁVEL por construção — a segunda passada encontra o hash já persistido e retorna
    ANTES de qualquer download (é o teste de duplicata). Por isso a identidade byte a byte
    é provada nos fixtures e, no pipeline, a identidade é a da relação entrada->saída,
    medida em duas execuções independentes.
    """
    alfa_bytes = _build_pdf(_LINES_ALFA)
    beta_bytes = _build_pdf(_LINES_BETA)

    # Nível 1: duas construções independentes dos MESMOS textos.
    assert _sha256(_build_pdf(_LINES_ALFA)) == _sha256(alfa_bytes), (
        "o fixture Alfa não é byte-estável entre construções"
    )
    assert _sha256(_build_pdf(_LINES_BETA)) == _sha256(beta_bytes), (
        "o fixture Beta não é byte-estável entre construções"
    )
    assert alfa_bytes != beta_bytes, "os dois fixtures deveriam ser diferentes"
    expected = {
        "Alfa": (_sha256(alfa_bytes), alfa_bytes),
        "Beta": (_sha256(beta_bytes), beta_bytes),
    }

    articles = []
    for marker, data in (("Alfa", alfa_bytes), ("Beta", beta_bytes)):
        url = pdf_pipeline.serve_pdf(f"https://{PDF_HOST}/artigo/{marker.lower()}.pdf", data)
        articles.append(await pdf_pipeline.create_article(marker=marker, pdf_url=url))

    job_ids, worker = await _dispatch_and_run(pdf_pipeline, arq_pool, run_arq_worker, articles)
    assert worker.jobs_complete == 2, (
        f"o worker deveria completar os 2 jobs (complete={worker.jobs_complete} "
        f"failed={worker.jobs_failed})"
    )
    assert worker.jobs_failed == 0

    _assert_only_expected_urls(
        pdf_pipeline.served,
        pdf_pipeline.unexpected,
        [f"https://{PDF_HOST}/artigo/{m.lower()}.pdf" for m in ("Alfa", "Beta")],
    )
    assert pdf_pipeline.handler_calls == 2

    page_counts: set[int | None] = set()
    statuses: set[Any] = set()
    for article, (marker, (expected_hash, data)) in zip(articles, expected.items(), strict=True):
        result = await _job_result(arq_pool, job_ids[articles.index(article)])
        assert result["status"] == "processed", f"artigo {marker}: {result}"

        meta = await verifier.pdf_metadata(article.id)
        assert meta is not None, f"artigo {marker}: nenhuma linha de pdf_metadata"
        extracted = _extract_with_pymupdf(data)
        assert meta.file_hash == expected_hash == _sha256(data)
        assert meta.extracted_text == extracted, f"artigo {marker}: texto extraído divergente"
        assert f"{marker} marker line" in meta.extracted_text, (
            f"artigo {marker}: o texto extraído não contém a linha-marcadora do SEU fixture"
        )
        assert meta.word_count == len(extracted.split())
        assert meta.processing_status == ProcessingStatus.COMPLETED

        # O arquivo em disco é o MESMO bytes que entrou, ainda depois da execução.
        assert Path(result["file_path"]).read_bytes() == data
        pdf_pipeline.file_paths.append(result["file_path"])
        page_counts.add(meta.page_count)
        statuses.add(meta.processing_status)

    # Identidade estrutural entre as duas execuções (mesma forma, entradas distintas).
    assert page_counts == {1}, f"page_count divergente entre as execuções: {page_counts}"
    assert statuses == {ProcessingStatus.COMPLETED}
    assert _sha256(alfa_bytes) != _sha256(beta_bytes), (
        "os dois artigos compartilharam o mesmo hash: a dedupe mascararia a 2a execução"
    )

    # Reconstruir os fixtures DEPOIS do pipeline reproduz o hash que ficou persistido:
    # a identidade byte a byte do gerador sobrevive ao run inteiro.
    for article, lines in zip(articles, (_LINES_ALFA, _LINES_BETA), strict=True):
        meta_pos = await verifier.pdf_metadata(article.id)
        assert meta_pos is not None
        assert meta_pos.file_hash == _sha256(_build_pdf(lines)), (
            "reconstruir o fixture depois do pipeline não reproduz o hash persistido"
        )


# --- (3) caminhos de falha que pertencem a este contrato -----------------------

#: Casos medidos: (nome, rota). Todos terminam em ``skipped`` pelo MESMO ``except``
#: de ``pdf_service.py:632-639``.
_FAILURE_CASES: tuple[tuple[str, _Route], ...] = (
    ("http_404", _Route(status_code=404, content_type="text/html", body=b"nao encontrado")),
    ("http_500", _Route(status_code=500, content_type="text/html", body=b"erro interno")),
    ("timeout", _Route(timeout=True)),
    (
        "payload_nao_pdf",
        _Route(content_type="text/html", body=b"<html><body>nao e um pdf</body></html>"),
    ),
    (
        "pdf_corrompido",
        _Route(content_type="application/pdf", body=b"%PDF-1.4\n%% bytes corrompidos da T16\n"),
    ),
)


@pytest.mark.parametrize(("case", "route"), _FAILURE_CASES, ids=[c for c, _ in _FAILURE_CASES])
async def test_falha_de_download_ou_extracao_vira_skipped_sem_linha(
    pdf_pipeline: PDFPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    run_arq_worker: RunArqWorker,
    case: str,
    route: _Route,
) -> None:
    """404, 500, timeout, payload não-PDF e ``%PDF`` corrompido: contrato MEDIDO.

    Em TODOS os casos o serviço engole o erro e devolve ``None`` — nem exceção, nem
    retry: o job termina com ``status == "skipped"``, ``jobs_failed == 0``, nenhuma linha
    em ``pdf_metadata``, ``articles.pdf_file_path`` continua NULL e nenhum arquivo sobra no
    storage. O ``ProcessingStatus.FAILED`` é inalcançável por este caminho (observação
    registrada no docstring do módulo).

    O URL termina em ``.pdf`` mesmo nos casos não-PDF de propósito: prova que a recusa vem
    dos magic bytes (``content.startswith(b"%PDF")``) e da validação estrutural, não da
    extensão da URL.
    """
    url = pdf_pipeline.serve(f"https://{PDF_HOST}/artigo/falha-{case}.pdf", route)
    article = await pdf_pipeline.create_article(marker=f"Falha {case}", pdf_url=url)

    job_ids, worker = await _dispatch_and_run(pdf_pipeline, arq_pool, run_arq_worker, [article])
    assert worker.jobs_failed == 0, (
        f"[{case}] o job morreu (jobs_failed={worker.jobs_failed}): o pipeline deveria "
        "engolir a falha e devolver skipped"
    )
    assert worker.jobs_complete == 1, f"[{case}] jobs_complete={worker.jobs_complete}"

    result = await _job_result(arq_pool, job_ids[0])
    assert result["status"] == "skipped", f"[{case}] resultado do job: {result}"

    _assert_only_expected_urls(pdf_pipeline.served, pdf_pipeline.unexpected, [url])
    assert pdf_pipeline.handler_calls == 1, f"[{case}] chamadas HTTP: {pdf_pipeline.handler_calls}"

    assert await verifier.pdf_metadata(article.id) is None, f"[{case}] linha criada em pdf_metadata"
    columns = await verifier.article_pdf_columns(article.id)
    assert columns is not None
    assert columns.pdf_file_path is None, (
        f"[{case}] pdf_file_path preenchido: {columns.pdf_file_path}"
    )
    assert columns.pdf_file_size is None
    assert pdf_pipeline.files_on_disk() == [], (
        f"[{case}] artefato órfão no storage: {pdf_pipeline.files_on_disk()}"
    )


async def test_artigo_que_ja_tem_pdf_nao_chama_http(
    pdf_pipeline: PDFPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    run_arq_worker: RunArqWorker,
) -> None:
    """Artigo que já tem PDF retorna ANTES de qualquer chamada HTTP.

    A asserção forte é ``handler_calls == 0``: não basta "nenhuma linha nova" (isso um
    download que falhasse também produziria). O curto-circuito está em
    ``pdf_service.py:436-438`` (``if article.pdf_file_path: return None``), antes do
    ``except`` que engole falhas — por isso aqui o ``skipped`` significa "não havia
    trabalho", não "falhou".
    """
    url = pdf_pipeline.serve_pdf(f"https://{PDF_HOST}/artigo/ja-tem.pdf", _build_pdf(_LINES_ALFA))
    existente = str(pdf_pipeline.upload_path / "ja-existe.pdf")
    article = await pdf_pipeline.create_article(
        marker="Ja Tem Pdf", pdf_url=url, pdf_file_path=existente
    )

    job_ids, worker = await _dispatch_and_run(pdf_pipeline, arq_pool, run_arq_worker, [article])
    assert worker.jobs_failed == 0
    assert worker.jobs_complete == 1

    result = await _job_result(arq_pool, job_ids[0])
    assert result["status"] == "skipped", f"resultado do job: {result}"

    # O ponto do teste: NENHUMA requisição chegou à fronteira HTTP.
    assert pdf_pipeline.handler_calls == 0, (
        "o artigo que já tem PDF chamou a fronteira HTTP: "
        f"served={pdf_pipeline.served} unexpected={pdf_pipeline.unexpected}"
    )
    assert pdf_pipeline.served == []
    assert pdf_pipeline.unexpected == []

    assert await verifier.pdf_metadata(article.id) is None
    columns = await verifier.article_pdf_columns(article.id)
    assert columns is not None
    assert columns.pdf_file_path == existente, (
        f"o caminho pré-existente do artigo foi alterado: {columns.pdf_file_path!r}"
    )
    assert columns.pdf_file_size is None
    assert pdf_pipeline.files_on_disk() == []


async def test_duplicata_por_hash_remove_o_arquivo_e_nao_cria_linha(
    pdf_pipeline: PDFPipeline,
    verifier: Verifier,
    arq_pool: ArqRedis,
    run_arq_worker: RunArqWorker,
) -> None:
    """Duplicata por hash: descoberta DEPOIS do download, arquivo órfão removido.

    Dois artigos servidos com os MESMOS bytes, em DUAS execuções de worker SEQUENCIAIS. O
    primeiro persiste e grava o arquivo; o segundo baixa (a fronteira HTTP É chamada — ao
    contrário do artigo que já tem PDF), processa, encontra o hash já existente
    (``check_duplicate``, chamado em ``download_pdf_from_url``), REMOVE o arquivo
    recém-gravado e devolve ``None`` -> ``skipped``. Resultado: exatamente UMA linha de
    ``pdf_metadata`` para aquele hash e exatamente UM arquivo em disco. É o teste que separa
    os dois significados de ``skipped``.

    Por que SEQUENCIAL, e a corrida que isso NÃO prende
    ---------------------------------------------------

    Despachar os dois jobs no MESMO ``burst`` foi MEDIDO e NÃO é determinístico: o worker
    roda até ``max_jobs=10`` jobs CONCORRENTES, os dois passam pelo ``check_duplicate``
    (TOCTOU: nenhum dos dois commitou ainda), os dois inserem e o perdedor da corrida
    estoura ``UniqueViolationError`` em ``pdf_metadata_file_hash_key`` -> ``jobs_failed=1``,
    com o job inteiro falhando e o arquivo órfão removido pelo rollback. Qual dos dois
    perde depende do escalonamento. A pré-checagem de duplicata é, portanto, um paliativo:
    a garantia real é a constraint UNIQUE. Isso é uma **observação para o ledger**, não um
    defeito a corrigir nesta task (o contrato literal não fala de concorrência), e por isso
    o teste prende o caso sequencial — que é determinístico — em vez da corrida.
    """
    data = _build_pdf(_LINES_ALFA)
    file_hash = _sha256(data)
    url_a = pdf_pipeline.serve_pdf(f"https://{PDF_HOST}/artigo/dup-a.pdf", data)
    url_b = pdf_pipeline.serve_pdf(f"https://{PDF_HOST}/artigo/dup-b.pdf", data)
    article_a = await pdf_pipeline.create_article(marker="Dup A", pdf_url=url_a)
    article_b = await pdf_pipeline.create_article(marker="Dup B", pdf_url=url_b)

    # Execução 1: o artigo A baixa, processa e persiste.
    job_ids_a, worker_a = await _dispatch_and_run(
        pdf_pipeline, arq_pool, run_arq_worker, [article_a]
    )
    assert worker_a.jobs_complete == 1, (
        f"complete={worker_a.jobs_complete} failed={worker_a.jobs_failed} "
        f"retried={worker_a.jobs_retried}"
    )
    assert worker_a.jobs_failed == 0
    result_a = await _job_result(arq_pool, job_ids_a[0])
    assert result_a["status"] == "processed", f"resultado do primeiro job: {result_a}"
    assert result_a["article_id"] == article_a.id
    pdf_pipeline.file_paths.append(result_a["file_path"])

    # Execução 2, SEQUENCIAL: os MESMOS bytes chegam ao artigo B, agora já persistidos.
    job_ids_b, worker_b = await _dispatch_and_run(
        pdf_pipeline, arq_pool, run_arq_worker, [article_b]
    )
    assert worker_b.jobs_failed == 0, (
        f"o job do duplicado morreu (failed={worker_b.jobs_failed}): a duplicata deveria "
        "virar skipped, não erro"
    )
    assert worker_b.jobs_complete == 1
    result_b = await _job_result(arq_pool, job_ids_b[0])
    assert result_b["status"] == "skipped", f"resultado do job duplicado: {result_b}"

    _assert_only_expected_urls(pdf_pipeline.served, pdf_pipeline.unexpected, [url_a, url_b])
    assert pdf_pipeline.handler_calls == 2, (
        "a duplicata por hash só é descoberta DEPOIS do download: a fronteira HTTP "
        f"deveria ter sido chamada 2x, foi {pdf_pipeline.handler_calls}"
    )

    # Uma única linha para o hash, e nenhuma para o artigo duplicado.
    rows = await verifier.rows_with_hash(file_hash)
    assert [row.article_id for row in rows] == [article_a.id], f"linhas com o hash: {rows}"
    assert await verifier.pdf_metadata(article_b.id) is None, (
        "o artigo duplicado ganhou linha em pdf_metadata"
    )
    columns_b = await verifier.article_pdf_columns(article_b.id)
    assert columns_b is not None
    assert columns_b.pdf_file_path is None, "o artigo duplicado aponta para arquivo"

    # O arquivo do duplicado foi removido: sobra só o do primeiro.
    files = pdf_pipeline.files_on_disk()
    assert files == [Path(result_a["file_path"])], (
        f"o storage deveria ter só o arquivo do primeiro artigo: {files}"
    )


# --- (4) guardas anti-falso-verde (elas mesmas testadas) -----------------------


def test_guarda_de_urls_fora_do_mapa_e_detectada() -> None:
    """A guarda de rede REJEITA uma URL intrusa — ela não é decorativa.

    Sem este teste, ``_assert_only_expected_urls`` poderia ser um no-op (ou comparar
    conjuntos vazios) e toda a tese de "sem internet externa" ficaria sem prova. Aqui a
    guarda é chamada com uma URL fora do mapa controlado e TEM de levantar.
    """
    intrusa = "https://host-desconhecido.invalid/qualquer.pdf"
    with pytest.raises(AssertionError, match="fora do mapa controlado"):
        _assert_only_expected_urls(
            ["https://mock16.local/ok.pdf"], [intrusa], ["https://mock16.local/ok.pdf"]
        )
    with pytest.raises(AssertionError, match="diferentes das esperadas"):
        _assert_only_expected_urls(
            ["https://mock16.local/outra.pdf"], [], ["https://mock16.local/ok.pdf"]
        )
    # E o caminho feliz NÃO levanta.
    _assert_only_expected_urls(["https://mock16.local/ok.pdf"], [], ["https://mock16.local/ok.pdf"])


async def test_guarda_da_fila_rejeita_job_intruso(arq_pool: ArqRedis) -> None:
    """A guarda de fila REJEITA um job que não é deste teste.

    Um zset ``arq:queue`` com membro alheio é exatamente o cenário de risco: o worker
    ``burst`` drenaria o job de PDF de outra suíte e tentaria baixar de verdade. O intruso
    aqui é sintético (sem chave ``arq:job:`` e sem função associada) porque o alvo é a
    guarda, não o worker; ele é removido no ``finally`` para não sujar a fila real.
    """
    intruso = "t16-intruso-sem-funcao"
    await arq_pool.zadd(default_queue_name, {intruso: 1})
    try:
        with pytest.raises(AssertionError, match="jobs que não são deste teste"):
            await _assert_queue_only(arq_pool, [])
        with pytest.raises(AssertionError, match="jobs que não são deste teste"):
            await _assert_queue_only(arq_pool, ["outro-job-qualquer"])
    finally:
        await arq_pool.zrem(default_queue_name, intruso)
    assert intruso not in await _queue_members(arq_pool)
