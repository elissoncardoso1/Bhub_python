# ruff: noqa: ARG001, ARG002
"""Testes de injeção de dependência (Task 6 — T2.2 e T2.3 do plano BHub v1.1).

Casos do brief:
- ``dependency_overrides`` substitui SearchService em rota real;
- ``dependency_overrides`` substitui ClassificationService via ``ClassifierDep``;
- fluxo de PDF usa storage fake (``upload_path``) e client HTTP fake injetados;
- rota admin de exclusão usa ``PDFService`` injetado (sem monkey-patching);
- job ARQ e executor inline aceitam serviço/fábrica de PDF injetados;
- ``OpenGraphService`` usa db explícito e é substituível via
  ``dependency_overrides`` na API e na rota web.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import ClassifierDep
from app.main import app


def make_pdf_bytes() -> bytes:
    """PDF mínimo e válido gerado via PyMuPDF (passa em ``_validate_pdf``)."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


class FakeResult:
    def __init__(self, obj):
        self.obj = obj

    def scalar_one_or_none(self):
        return self.obj


class FakeDB:
    """Sessão fake: nenhuma duplicata persistida."""

    async def execute(self, *_args, **_kwargs):
        return FakeResult(None)


# ---------------------------------------------------------------------------
# dependency_overrides: SearchService (rota real /api/v1/search/stats)
# ---------------------------------------------------------------------------


async def test_dependency_overrides_substitui_search_service(client):
    from app.api.deps import get_search_service

    class FakeSearchService:
        async def get_search_stats(self) -> dict:
            return {"total_articles": 42, "fonte": "fake"}

    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()

    response = await client.get("/api/v1/search/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["fonte"] == "fake"
    assert data["total_articles"] == 42


# ---------------------------------------------------------------------------
# dependency_overrides: ClassificationService (provider ClassifierDep)
# ---------------------------------------------------------------------------


async def test_dependency_overrides_substitui_classification_service():
    from app.api.deps import get_classification_service

    di_app = FastAPI()

    @di_app.get("/classify")
    async def classify(service: ClassifierDep) -> dict:
        slug, confidence = await service.classify("texto")
        return {"category": slug, "confidence": confidence}

    class FakeClassificationService:
        async def classify(self, text: str) -> tuple[str, float]:
            return ("autismo", 0.95)

    di_app.dependency_overrides[get_classification_service] = (
        lambda: FakeClassificationService()
    )

    async with AsyncClient(
        transport=ASGITransport(app=di_app),
        base_url="http://test",
    ) as ac:
        response = await ac.get("/classify")

    assert response.status_code == 200
    assert response.json() == {"category": "autismo", "confidence": 0.95}


# ---------------------------------------------------------------------------
# T2.2 — PDFService: storage e client HTTP injetáveis
# ---------------------------------------------------------------------------


async def test_pdf_service_usa_storage_injetado(tmp_path):
    """Fluxo de PDF pode usar storage fake: ``process_pdf`` grava no caminho injetado."""
    import io

    from app.services.pdf_service import PDFService

    storage = tmp_path / "pdfs"
    service = PDFService(upload_path=storage)

    result = await service.process_pdf(io.BytesIO(make_pdf_bytes()), "arquivo.pdf")

    saved = Path(result["file_path"])
    assert storage in saved.parents
    assert saved.exists()


def test_pdf_service_padrao_mantem_storage_de_config():
    from app.config import settings
    from app.services.pdf_service import PDFService

    assert PDFService().upload_path == settings.pdf_upload_path


async def test_pdf_service_usa_client_http_injetado(tmp_path):
    """Download usa o client HTTP injetado — nenhum ``httpx.AsyncClient`` criado."""
    from app.services.pdf_service import PDFService

    class FakeResponse:
        headers = {"content-type": "application/pdf"}
        content = make_pdf_bytes()

        def raise_for_status(self) -> None:
            pass

    class FakeAsyncClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def get(self, url: str) -> FakeResponse:
            self.calls.append(url)
            return FakeResponse()

    http_client = FakeAsyncClient()
    service = PDFService(upload_path=tmp_path, http_client=http_client)

    data = await service.download_pdf_from_url(
        "https://example.com/p.pdf", "Título", FakeDB()
    )

    assert http_client.calls == ["https://example.com/p.pdf"]
    assert data is not None
    assert Path(data["file_path"]).exists()


# ---------------------------------------------------------------------------
# T2.2 — Rotas admin usam o provider (substituível, sem monkey-patching)
# ---------------------------------------------------------------------------


async def test_rota_admin_delete_usa_pdf_service_injetado(client, auth_headers, db_session):
    from app.api.deps import get_pdf_service
    from app.models import Article

    article = Article(
        title="Com PDF",
        is_published=True,
        pdf_file_path="/storage/alvo.pdf",
    )
    db_session.add(article)
    await db_session.commit()

    deletados: list[str] = []

    class FakePDFService:
        def delete_pdf(self, file_path: str) -> bool:
            deletados.append(file_path)
            return True

    app.dependency_overrides[get_pdf_service] = lambda: FakePDFService()

    response = await client.delete(
        f"/api/v1/admin/articles/{article.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert deletados == ["/storage/alvo.pdf"]


def test_rotas_admin_nao_instanciam_pdf_service_diretamente():
    from app.api.v1.admin import articles as admin_articles

    source = inspect.getsource(admin_articles)
    assert "PDFService(" not in source


# ---------------------------------------------------------------------------
# T2.2 — Jobs/worker: injeção via contexto/factory (sem FastAPI)
# ---------------------------------------------------------------------------


async def test_task_download_pdf_aceita_pdf_service_do_contexto():
    import app.jobs.tasks as jobs_tasks

    chamadas: list[tuple[int, str | None]] = []

    class FakePDFService:
        async def process_article_pdf(self, article_id, pdf_url=None, db=None):
            chamadas.append((article_id, pdf_url))
            return {"article_id": article_id, "file_path": "/tmp/f.pdf", "file_hash": "h"}

    result = await jobs_tasks.task_download_pdf(
        {"db": None, "pdf_service": FakePDFService()},
        3,
        "https://x/a.pdf",
    )

    assert chamadas == [(3, "https://x/a.pdf")]
    assert result["status"] == "processed"


async def test_inline_queue_aceita_factory_de_pdf_service():
    from app.interfaces.task_queue import InlineTaskQueue

    executados: list[int] = []

    class FakePDFService:
        async def process_article_pdf(self, article_id, pdf_url=None, db=None):
            executados.append(article_id)
            return None

    queue = InlineTaskQueue(pdf_service_factory=FakePDFService)
    job_id = await queue.dispatch_pdf(article_id=5, pdf_url=None)
    await queue.wait_pending()

    assert job_id == "inline-pdf-5"
    assert executados == [5]

