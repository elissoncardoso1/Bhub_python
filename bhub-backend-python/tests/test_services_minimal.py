from types import SimpleNamespace

import pytest

from app.services.background_tasks import classify_article_task, download_pdf_task
from app.services.classification_service import ClassificationService
from app.services.feed_aggregator import FeedAggregatorService
from app.web.routes import _is_htmx


def test_classification_service_normalize_slug():
    slug = ClassificationService.normalize_slug("Ártico -- Teste 123")
    assert slug.replace("-", "") == "articoteste123"


@pytest.mark.asyncio
async def test_classification_service_classify_with_manager(monkeypatch):
    class FakeAIManager:
        async def classify(self, text):
            return ("clinica", 0.9, "fake")

        providers = {}

    result = await ClassificationService.classify_with_multiple_categories(
        db=None, text="titulo resumo", ai_manager=FakeAIManager(), min_confidence=0.3
    )
    assert result == [("clinica", 0.9)]


@pytest.mark.asyncio
async def test_feed_aggregator_process_feed_entry_existing(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return True

    class FakeDB:
        async def execute(self, *_args, **_kwargs):
            return FakeResult()

    agg = FeedAggregatorService(db=FakeDB())
    article_id, article_data = await agg._process_feed_entry(
        feed=SimpleNamespace(id=1, journal_name=None), entry={"id": "x"}
    )
    assert article_id is None
    assert article_data is None


def test_is_htmx_helper():
    class Req:
        headers = {"hx-request": "true"}

    assert _is_htmx(Req()) is True


@pytest.mark.asyncio
async def test_classify_article_task_no_article(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeDB:
        async def execute(self, *_args, **_kwargs):
            return FakeResult()

    class FakeSessionCtx:
        async def __aenter__(self):
            return FakeDB()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.services.background_tasks.get_session_context", lambda: FakeSessionCtx()
    )

    await classify_article_task(article_id=999)


@pytest.mark.asyncio
async def test_download_pdf_task_no_article(monkeypatch):
    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeDB:
        async def execute(self, *_args, **_kwargs):
            return FakeResult()

    class FakeSessionCtx:
        async def __aenter__(self):
            return FakeDB()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.services.background_tasks.get_session_context", lambda: FakeSessionCtx()
    )

    await download_pdf_task(article_id=999)
