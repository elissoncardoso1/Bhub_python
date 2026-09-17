# ruff: noqa: ARG001, ARG002
"""Testes de idempotência dos jobs ARQ (T1.4 — plano BHub v1.1).

Reexecução do mesmo job não deve duplicar metadados PDF, associações,
classificações ou arquivos. Casos de unidade sobre banco sqlite em
memória (worker real é Task 14):

- download cujo hash já está persistido não deixa arquivo órfão;
- commit falho não deixa arquivo para a reexecução duplicar;
- classificação reexecutada não duplica categorias/associações;
- download reexecutado não baixa nem persiste de novo;
- metadados pré-existentes são atualizados, não duplicados.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.jobs.tasks import task_classify_article, task_download_pdf
from app.models import (
    Article,
    Category,
    PDFMetadata,
    ProcessingStatus,
    article_categories,
)
from app.services.pdf_service import PDFService
from tests.conftest import async_session_test


def make_pdf_data(file_path: str) -> dict:
    """Payload de download bem-sucedido, como o de ``process_pdf``."""
    return {
        "file_hash": "hash123",
        "file_path": file_path,
        "file_size": 3,
        "original_filename": "paper.pdf",
        "page_count": 1,
        "word_count": 10,
        "extracted_text": "texto",
        "pdf_info": {},
    }


class _FakeResponse:
    status_code = 200
    headers = {"content-type": "application/pdf"}
    content = b"%PDF-1.4-fake"

    def raise_for_status(self) -> None:
        pass


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def get(self, url):  # noqa: ARG002
        return _FakeResponse()


async def run_classify_job(article_id: int) -> dict:
    """Executa task_classify_article como o worker: sessão nova por job."""
    async with async_session_test() as session:
        return await task_classify_article({"db": session}, article_id)


async def run_pdf_job(article_id: int, pdf_url: str) -> dict:
    """Executa task_download_pdf como o worker: sessão nova por job."""
    async with async_session_test() as session:
        return await task_download_pdf({"db": session}, article_id, pdf_url)


async def test_pdf_job_hash_ja_persistido_nao_deixa_arquivo_orfao(
    db_session, monkeypatch, tmp_path
):
    """Reexecução/segundo job com hash já persistido não duplica arquivo em disco."""
    # Artigo A já tem o PDF persistido com hash123.
    article_a = Article(
        title="Paper A",
        is_open_access=True,
        pdf_url="https://example.com/a.pdf",
    )
    db_session.add(article_a)
    await db_session.flush()
    article_a.pdf_file_path = "/storage/a.pdf"
    db_session.add(
        PDFMetadata(
            article_id=article_a.id,
            file_hash="hash123",
            processing_status=ProcessingStatus.COMPLETED,
        )
    )
    await db_session.commit()

    # Job para o artigo B baixa o MESMO conteúdo (mesmo hash).
    article_b = Article(
        title="Paper B",
        is_open_access=True,
        pdf_url="https://example.com/b.pdf",
    )
    db_session.add(article_b)
    await db_session.commit()

    async def fake_process_pdf(self, file, filename):  # noqa: ARG002
        path = tmp_path / "duplicado.pdf"
        path.write_bytes(b"%PDF-1")
        return make_pdf_data(str(path))

    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(PDFService, "process_pdf", fake_process_pdf)

    result = await run_pdf_job(article_b.id, article_b.pdf_url)

    assert result["status"] == "skipped"
    assert not (tmp_path / "duplicado.pdf").exists()  # sem arquivo órfão

    async with async_session_test() as session:
        refreshed = await session.get(Article, article_b.id)
        metas = (
            (
                await session.execute(
                    select(PDFMetadata).where(PDFMetadata.article_id == article_b.id)
                )
            )
            .scalars()
            .all()
        )

    assert refreshed.pdf_file_path is None
    assert metas == []


async def test_pdf_job_commit_falho_nao_deixa_arquivo_para_reexecucao(
    db_session, monkeypatch, tmp_path
):
    """Commit falho: rollback não pode deixar o arquivo baixado (a reexecução
    baixaria um segundo arquivo, duplicando em disco)."""
    article = Article(
        title="Paper C",
        is_open_access=True,
        pdf_url="https://example.com/c.pdf",
    )
    db_session.add(article)
    await db_session.commit()

    path = tmp_path / "commit-falho.pdf"
    path.write_bytes(b"%PDF-1")

    async def fake_download(self, url, title, db):  # noqa: ARG002
        return make_pdf_data(str(path))

    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake_download)

    async with async_session_test() as session:

        async def commit_que_falha():
            raise RuntimeError("falha transiente no commit")

        monkeypatch.setattr(session, "commit", commit_que_falha)

        with pytest.raises(RuntimeError, match="falha transiente no commit"):
            await task_download_pdf({"db": session}, article.id, article.pdf_url)

    assert not path.exists()  # RED: arquivo permanece após o rollback

    async with async_session_test() as session:
        metas = (
            (await session.execute(select(PDFMetadata).where(PDFMetadata.article_id == article.id)))
            .scalars()
            .all()
        )
    assert metas == []


async def test_classify_job_reexecucao_nao_duplica_categorias_nem_associacoes(
    db_session, monkeypatch
):
    """Prova T1.4: reexecutar task_classify_article não duplica categorias
    (get_or_create) nem associações (check-then-act na tabela)."""
    article = Article(
        title="Estudo sobre reforçamento em crianças autistas",
        abstract="Análise aplicada do comportamento com reforço diferencial",
        keywords="autismo, ABA",
    )
    db_session.add(article)
    await db_session.commit()

    class FakeAIManager:
        async def classify(self, text):  # noqa: ARG002
            return ("autismo", 0.9)

    monkeypatch.setattr("app.ai.get_ai_manager", lambda: FakeAIManager())
    monkeypatch.setattr("app.jobs.tasks.get_ai_manager", lambda: FakeAIManager(), raising=False)
    # Sem fallback ML: is_initialized() False despenca direto no heurístico.
    from app.ml import EmbeddingClassifier

    monkeypatch.setattr(EmbeddingClassifier, "is_initialized", staticmethod(lambda: False))

    first = await run_classify_job(article.id)
    assert first["category"] == "autismo"

    second = await run_classify_job(article.id)  # reexecução do mesmo job

    assert second["category"] == first["category"]

    async with async_session_test() as session:
        categorias = (
            (await session.execute(select(Category).where(Category.slug == "autismo")))
            .scalars()
            .all()
        )
        associacoes = (
            (
                await session.execute(
                    select(article_categories).where(article_categories.c.article_id == article.id)
                )
            )
            .scalars()
            .all()
        )

    assert len(categorias) == 1  # categoria não duplicada
    assert len(associacoes) == 1  # associação não duplicada


async def test_pdf_job_reexecucao_nao_duplica_metadados_nem_arquivo(db_session, monkeypatch):
    """Prova T1.4: reexecutar task_download_pdf é no-op — early-return em
    pdf_file_path impede novo download; metadados permanecem 1 por artigo."""
    path = "/tmp/teste-idempotencia-nao-existe.pdf"
    article = Article(
        title="Paper D",
        is_open_access=True,
        pdf_url="https://example.com/d.pdf",
        pdf_file_path=path,
        pdf_file_size=3,
    )
    db_session.add(article)
    await db_session.flush()
    db_session.add(
        PDFMetadata(
            article_id=article.id,
            file_hash="hash-d",
            processing_status=ProcessingStatus.COMPLETED,
        )
    )
    await db_session.commit()

    downloads: list[str] = []

    async def download_nunca_chamado(self, url, title, db):  # noqa: ARG002
        downloads.append(url)
        raise AssertionError("reexecução não deve baixar PDF novamente")

    monkeypatch.setattr(PDFService, "download_pdf_from_url", download_nunca_chamado)

    result = await run_pdf_job(article.id, article.pdf_url)

    assert result["status"] == "skipped"
    assert downloads == []

    async with async_session_test() as session:
        metas = (
            (await session.execute(select(PDFMetadata).where(PDFMetadata.article_id == article.id)))
            .scalars()
            .all()
        )
    assert len(metas) == 1
    assert metas[0].file_hash == "hash-d"


async def test_pdf_job_metadados_preexistentes_sao_atualizados_nao_duplicados(
    db_session, monkeypatch, tmp_path
):
    """Prova T1.4: PDFMetadata tem upsert por artigo — artigo PENDING sem
    arquivo recebe o PDF e os metadados existentes são atualizados (1 linha)."""
    article = Article(
        title="Paper E",
        is_open_access=True,
        pdf_url="https://example.com/e.pdf",
    )
    db_session.add(article)
    await db_session.flush()
    db_session.add(
        PDFMetadata(
            article_id=article.id,
            file_hash="hash-e-antigo",
            processing_status=ProcessingStatus.PENDING,
        )
    )
    await db_session.commit()

    real_file = tmp_path / "paper-e.pdf"
    real_file.write_bytes(b"%PDF-1")

    async def fake_download(self, url, title, db):  # noqa: ARG002
        return make_pdf_data(str(real_file))

    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake_download)

    result = await run_pdf_job(article.id, article.pdf_url)

    assert result["status"] == "processed"

    async with async_session_test() as session:
        metas = (
            (await session.execute(select(PDFMetadata).where(PDFMetadata.article_id == article.id)))
            .scalars()
            .all()
        )
        refreshed = await session.get(Article, article.id)

    assert len(metas) == 1  # atualizou, não duplicou
    assert metas[0].file_hash == "hash123"
    assert metas[0].processing_status == ProcessingStatus.COMPLETED
    assert refreshed.pdf_file_path == str(real_file)
