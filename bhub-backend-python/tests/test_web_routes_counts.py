import pytest

from app.web.routes import _get_categories_with_counts


class FakeRow:
    def __init__(self, id, name, count):
        self.id = id
        self.name = name
        self.article_count = count


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeDB:
    async def execute(self, stmt):
        return FakeResult([FakeRow(1, "Cat", None), FakeRow(2, "Other", 3)])


@pytest.mark.asyncio
async def test_get_categories_with_counts():
    rows = await _get_categories_with_counts(FakeDB())
    assert rows == [
        {"id": 1, "name": "Cat", "article_count": 0},
        {"id": 2, "name": "Other", "article_count": 3},
    ]
