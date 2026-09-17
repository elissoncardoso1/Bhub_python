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

    di_app.dependency_overrides[get_classification_service] = lambda: FakeClassificationService()

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

    data = await service.download_pdf_from_url("https://example.com/p.pdf", "Título", FakeDB())

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


# ---------------------------------------------------------------------------
# T2.3 — OpenGraphService: db explícito e substituível
# ---------------------------------------------------------------------------


async def test_opengraph_service_usa_db_explicito(tmp_path, db_session):  # noqa: ARG001
    """``get_article_metadata`` com db explícito NÃO abre sessão própria."""
    from app.services.opengraph_service import OpenGraphService

    service = OpenGraphService(cache_dir=tmp_path)

    consultas: list[str] = []

    class SpyDB:
        async def execute(self, *_args, **_kwargs):
            consultas.append("execute")
            return FakeResult(None)

    metadata = await service.get_article_metadata(1, "https://bhub.ex", db=SpyDB())

    assert consultas == ["execute"]  # usou o db injetado, não get_session_context
    assert metadata["og:site_name"] == "BHub"


def test_opengraph_service_sem_import_de_sessao_no_modulo():
    """T2.3: nenhuma dependência de sessão no escopo de módulo do serviço —
    o banco trafega por construtor/argumento. (O fallback lazy dentro de
    ``get_article_metadata`` cobre call sites fora de rotas e é o único
    ponto em que ``get_session_context`` aparece.)"""
    import inspect

    import app.services.opengraph_service as og_module

    source = inspect.getsource(og_module)
    assert (
        "from app.database import get_session_context"
        not in source.split("async def get_article_metadata")[0]
    )


async def test_opengraph_service_substituivel_na_api(client, db_session):
    from app.api.deps import get_opengraph_service
    from app.models import Article

    article = Article(title="Artigo OG", is_published=True)
    db_session.add(article)
    await db_session.commit()

    class FakeOpenGraphService:
        async def get_article_metadata(self, article_id: int, base_url: str) -> dict:
            return {"og:title": "FAKE-OG", "og:site_name": "BHub"}

    app.dependency_overrides[get_opengraph_service] = lambda: FakeOpenGraphService()

    response = await client.get(f"/api/v1/og/articles/{article.id}/json")

    assert response.status_code == 200
    assert response.json()["og:title"] == "FAKE-OG"


async def test_opengraph_service_substituivel_na_rota_web(client, db_session):
    """Rota web article_detail usa o provider — sem instanciar OpenGraphService."""
    from app.api.deps import get_opengraph_service
    from app.models import Article

    article = Article(title="Artigo Web OG", is_published=True)
    db_session.add(article)
    await db_session.commit()

    class FakeOpenGraphService:
        async def get_article_metadata(self, article_id: int, base_url: str, db=None) -> dict:
            return {
                "og:title": "FAKE-WEB",
                "og:description": "desc",
                "og:image": f"{base_url}/fake.png",
                "description": "DESCRICAO-DO-FAKE-OG",
            }

    app.dependency_overrides[get_opengraph_service] = lambda: FakeOpenGraphService()

    response = await client.get(f"/articles/{article.id}")

    assert response.status_code == 200
    # a meta description vem dos metadados do serviço injetado — se o
    # override não funcionasse, viria o abstract do artigo (aqui ausente).
    assert "DESCRICAO-DO-FAKE-OG" in response.text


def test_rota_web_nao_instancia_opengraph_service():
    from app.web import routes as web_routes

    source = inspect.getsource(web_routes)
    assert "OpenGraphService()" not in source
    assert "from app.services.opengraph_service import OpenGraphService" not in source
