import pytest

from app.web.routes import ArticleFilters, _fetch_articles


class FakeRow:
    def __init__(self, id, name, count):
        self.id = id
        self.name = name
        self.article_count = count


class FakeResult:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def fetchall(self):
        return self._rows

    def scalars(self):
        return self

    def all(self):
        return []

    def scalar_one_or_none(self):
        return self._scalar


class FakeDB:
    async def execute(self, stmt):
        return FakeResult()

    async def scalar(self, stmt):
        return 0


@pytest.mark.asyncio
async def test_fetch_articles_empty_result():
    db = FakeDB()
    filters = ArticleFilters(
        search=None,
        category_ids=(),
        feed_id=None,
        highlighted=None,
        has_pdf=None,
        is_open_access=None,
        source_category="journal",
        sort_by="publication_date",
        sort_order="asc",
        page=1,
        page_size=20,
        date_from=None,
        date_to=None,
        search_type="text",
    )
    articles, total, offset = await _fetch_articles(db, filters)
    assert articles == []
    assert total == 0
    assert offset == 0
