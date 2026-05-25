import pytest

from app.models import Category
from app.services.classification_service import ClassificationService


class FakeResult:
    def __init__(self, obj=None):
        self.obj = obj

    def scalar_one_or_none(self):
        return self.obj


class FakeDB:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.flushed = False

    async def execute(self, *_args, **_kwargs):
        return FakeResult(self.existing)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_get_or_create_category_creates_new(monkeypatch):
    db = FakeDB(existing=None)
    category = await ClassificationService.get_or_create_category(db, slug="nova-cat")
    assert isinstance(category, Category)
    assert db.flushed is True
    assert category.slug == "nova-cat"


@pytest.mark.asyncio
async def test_get_or_create_category_returns_existing(monkeypatch):
    existing = Category(name="Old", slug="old")
    db = FakeDB(existing=existing)
    category = await ClassificationService.get_or_create_category(db, slug="old")
    assert category is existing
    assert db.added == []
