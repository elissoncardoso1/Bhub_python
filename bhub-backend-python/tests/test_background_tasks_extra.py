# ruff: noqa: ARG001, ARG002
import pytest

from app.services.background_tasks import classify_article_task


class StubArticle:
    def __init__(self):
        self.id = 1
        self.title = "t"
        self.abstract = "a"
        self.keywords = "k"
        self.journal_name = None
        self.doi = None
        self.impact_score = None
        self.classification_confidence = None
        self.pdf_url = "https://example.com/file.pdf"
        self.is_open_access = True
        self.pdf_file_path = None


class FakeResult:
    def __init__(self, obj):
        self.obj = obj

    def scalar_one_or_none(self):
        return self.obj

    def first(self):
        return None


class FakeDB:
    def __init__(self, article):
        self.article = article
        self.committed = False
        self.added = []

    async def execute(self, *_args, **_kwargs):
        return FakeResult(self.article)

    async def commit(self):
        self.committed = True

    def add(self, obj):
        self.added.append(obj)


class FakeSessionCtx:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_classify_article_task_happy(monkeypatch):
    article = StubArticle()
    db = FakeDB(article)

    async def fake_classify_with_multiple_categories(**_kwargs):
        return [("clinica", 0.8)]

    async def fake_assign_categories_to_article(**_kwargs):
        return [type("Cat", (), {"name": "Cat"})()]

    async def fake_calc_impact(**_kwargs):
        return 7.0

    monkeypatch.setattr(
        "app.services.background_tasks.get_session_context", lambda: FakeSessionCtx(db)
    )
    import app.services.background_tasks as bt

    FakeCS = type(
        "FakeCS",
        (),
        {
            "classify_with_multiple_categories": staticmethod(fake_classify_with_multiple_categories),
            "assign_categories_to_article": staticmethod(fake_assign_categories_to_article),
        },
    )
    bt.ClassificationService = FakeCS
    monkeypatch.setattr("app.services.classification_service.ClassificationService", FakeCS, raising=False)

    FakeImpact = type("FakeImpact", (), {"calculate_impact": staticmethod(fake_calc_impact)})
    bt.ImpactRatingService = FakeImpact
    monkeypatch.setattr("app.ml.impact_rating.ImpactRatingService", FakeImpact, raising=False)

    class FakeAI:
        async def classify(self, text):
            return ("clinica", 0.9, "fake")

        providers = {}

    bt.get_ai_manager = lambda: FakeAI()
    monkeypatch.setattr("app.ai.get_ai_manager", bt.get_ai_manager, raising=False)

    await classify_article_task(article_id=1)
    assert db.committed is True
    assert article.impact_score is not None
    assert article.classification_confidence == 0.8
