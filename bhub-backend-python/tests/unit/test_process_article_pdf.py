# ruff: noqa: ARG001
"""Testes unitários da operação transacional process_article_pdf (T1.3).

RED→GREEN para o épico 1 do plano BHub v1.1:
- ``PDFService.process_article_pdf`` concentra obtenção do artigo, download,
  validação, extração de metadados, persistência e commit/rollback controlado.
- ``task_download_pdf`` não importa ``background_tasks`` — chama a operação
  transacional explícita de ``pdf_service``.
- InlineTaskQueue também roteia o download de PDF pela nova operação.
"""

from __future__ import annotations

import pytest

import app.jobs.tasks as jobs_tasks
from app.models import ProcessingStatus


class StubArticle:
    def __init__(self, *, pdf_url="https://example.com/file.pdf"):
        self.id = 1
        self.title = "t"
        self.abstract = "a"
        self.pdf_url = pdf_url
        self.is_open_access = True
        self.pdf_file_path = None
        self.original_url = None


class FakeResult:
    def __init__(self, obj):
        self.obj = obj

    def scalar_one_or_none(self):
        return self.obj


class FakeDB:
    def __init__(self, article, pdf_metadata=None):
        self.article = article
        self.pdf_metadata = pdf_metadata
        self.committed = False
        self.rolled_back = False
        self.added = []
        self.execute_calls = 0

    async def execute(self, *_args, **_kwargs):
        self.execute_calls += 1
        # alterna: 1ª chamada busca o artigo, demais buscam PDFMetadata
        if self.execute_calls == 1:
            return FakeResult(self.article)
        return FakeResult(self.pdf_metadata)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    def add(self, obj):
        self.added.append(obj)


class FakePDFService:
    """Substitui PDFService.download_pdf_from_url/check_duplicate."""

    def __init__(self, pdf_data=None, duplicate=False):
        self.pdf_data = pdf_data
        self.duplicate = duplicate
        self.urls_tried: list[str] = []

    async def download_pdf_from_url(self, url, title, db):  # noqa: ARG002
        self.urls_tried.append(url)
        return self.pdf_data

    async def check_duplicate(self, file_hash, db):  # noqa: ARG002
        return self.duplicate


PDF_DATA = {
    "file_hash": "hash123",
    "file_path": "/tmp/fake/file.pdf",
    "file_size": 3,
    "original_filename": "f.pdf",
    "page_count": 1,
    "word_count": 10,
    "extracted_text": "txt",
    "pdf_info": {},
}


# ---------------------------------------------------------------------------
# task_download_pdf desacoplado de background_tasks
# ---------------------------------------------------------------------------


def test_task_download_pdf_nao_importa_background_tasks():
    """Critério de aceite T1.3: app/jobs/tasks.py não referencia background_tasks."""
    import inspect

    source = inspect.getsource(jobs_tasks)
    assert "background_tasks" not in source


async def test_task_download_pdf_usa_operacao_transacional(monkeypatch):
    """task_download_pdf chama pdf_service.process_article_pdf com (article_id, pdf_url)."""
    called: list[tuple[int, str | None]] = []

    async def fake_process(self, article_id, pdf_url=None, db=None):
        called.append((article_id, pdf_url))
        return {"article_id": article_id, "file_path": "/tmp/x.pdf", "file_hash": "h"}

    monkeypatch.setattr("app.services.pdf_service.PDFService.process_article_pdf", fake_process)

    result = await jobs_tasks.task_download_pdf({"db": None}, 7, "https://x/a.pdf")

    assert called == [(7, "https://x/a.pdf")]
    assert result["article_id"] == 7
    assert result["status"] == "processed"


def test_jobs_module_nao_importa_background_tasks_em_runtime(monkeypatch):
    """Import de app.jobs.tasks não puxa app.services.background_tasks."""
    import subprocess
    import sys

    code = (
        "import sys, app.jobs.tasks as t; "
        "assert 'app.services.background_tasks' not in sys.modules, 'importou background_tasks'; "
        "print('ok')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout


# ---------------------------------------------------------------------------
# process_article_pdf: operação transacional explícita
# ---------------------------------------------------------------------------


async def test_process_article_pdf_baixa_persiste_e_commite(monkeypatch, tmp_path):
    from app.services.pdf_service import PDFService

    article = StubArticle()
    db = FakeDB(article, pdf_metadata=None)
    fake = FakePDFService(pdf_data=PDF_DATA)
    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake.download_pdf_from_url)
    monkeypatch.setattr(PDFService, "check_duplicate", fake.check_duplicate)

    service = PDFService()
    result = await service.process_article_pdf(1, "https://example.com/file.pdf", db=db)

    assert result is not None
    assert result["article_id"] == 1
    assert db.committed is True
    assert db.rolled_back is False
    assert article.pdf_file_path == PDF_DATA["file_path"]
    assert article.pdf_file_size == PDF_DATA["file_size"]
    assert len(db.added) == 1
    meta = db.added[0]
    assert meta.file_hash == "hash123"
    assert meta.processing_status == ProcessingStatus.COMPLETED


async def test_process_article_pdf_artigo_inexistente_retorna_none(monkeypatch):
    from app.services.pdf_service import PDFService

    db = FakeDB(None)
    fake = FakePDFService(pdf_data=PDF_DATA)
    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake.download_pdf_from_url)
    monkeypatch.setattr(PDFService, "check_duplicate", fake.check_duplicate)

    service = PDFService()
    result = await service.process_article_pdf(999, "https://x/a.pdf", db=db)

    assert result is None
    assert db.committed is False
    assert fake.urls_tried == []


async def test_process_article_pdf_sem_url_retorna_none(monkeypatch):
    from app.services.pdf_service import PDFService

    article = StubArticle(pdf_url=None)
    article.original_url = None
    db = FakeDB(article)
    fake = FakePDFService(pdf_data=PDF_DATA)
    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake.download_pdf_from_url)
    monkeypatch.setattr(PDFService, "check_duplicate", fake.check_duplicate)

    service = PDFService()
    result = await service.process_article_pdf(1, None, db=db)

    assert result is None
    assert db.committed is False


async def test_process_article_pdf_duplicado_nao_persiste(monkeypatch, tmp_path):
    from app.services.pdf_service import PDFService

    article = StubArticle()
    db = FakeDB(article)
    dup_file = tmp_path / "dup.pdf"
    dup_file.write_text("x")
    data = dict(PDF_DATA, file_path=str(dup_file))
    fake = FakePDFService(pdf_data=data, duplicate=True)
    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake.download_pdf_from_url)
    monkeypatch.setattr(PDFService, "check_duplicate", fake.check_duplicate)

    service = PDFService()
    result = await service.process_article_pdf(1, "https://example.com/file.pdf", db=db)

    assert result is None
    assert db.committed is False
    assert article.pdf_file_path is None
    assert not dup_file.exists()  # arquivo órfão removido


async def test_process_article_pdf_erro_transacional_rollback(monkeypatch):
    from app.services.pdf_service import PDFService

    article = StubArticle()
    db = FakeDB(article)

    async def boom(self, url, title, db):
        raise RuntimeError("falha no download")

    monkeypatch.setattr(PDFService, "download_pdf_from_url", boom)
    monkeypatch.setattr(PDFService, "check_duplicate", FakePDFService().check_duplicate)

    service = PDFService()
    with pytest.raises(RuntimeError, match="falha no download"):
        await service.process_article_pdf(1, "https://example.com/file.pdf", db=db)

    assert db.rolled_back is True
    assert db.committed is False


async def test_process_article_pdf_cria_propria_sessao_quando_db_none(monkeypatch):
    from app.services.pdf_service import PDFService

    article = StubArticle()
    db = FakeDB(article)
    fake = FakePDFService(pdf_data=PDF_DATA)

    class FakeSessionCtx:
        def __init__(self, inner):
            self.inner = inner

        async def __aenter__(self):
            return self.inner

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.database.get_session_context", lambda: FakeSessionCtx(db))
    monkeypatch.setattr(PDFService, "download_pdf_from_url", fake.download_pdf_from_url)
    monkeypatch.setattr(PDFService, "check_duplicate", fake.check_duplicate)

    service = PDFService()
    result = await service.process_article_pdf(1, "https://example.com/file.pdf")

    assert result is not None
    assert db.committed is True
