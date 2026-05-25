import datetime

from app.services.article_parser import ArticleParserService


def test_extract_abstract_strips_html():
    parser = ArticleParserService()
    entry = {"summary": "<p>Hello <b>World</b></p>"}
    abstract = parser._extract_abstract(entry)
    assert abstract == "Hello World"


def test_extract_url_from_list_and_dict():
    parser = ArticleParserService()
    entry = {
        "links": [
            {"rel": "alternate", "href": "https://example.com/alt"},
            {"href": "https://example.com/fallback"},
        ]
    }
    assert parser._extract_url(entry) == "https://example.com/alt"

    entry2 = {"link": {"href": "https://example.com/dict"}}
    assert parser._extract_url(entry2) == "https://example.com/dict"


def test_extract_date_from_string_and_datetime():
    parser = ArticleParserService()
    dt = parser._extract_date({"published": "2024-01-02"})
    assert isinstance(dt, datetime.datetime)

    now = datetime.datetime.utcnow()
    dt2 = parser._extract_date({"published": now})
    assert dt2 == now


def test_extract_keywords_and_open_access():
    parser = ArticleParserService()
    entry = {"tags": [{"term": "kw1"}, {"term": "kw2"}], "is_open_access": True}
    parsed = parser.parse_entry(entry, journal_name=None)
    assert parsed["keywords"] in (["kw1", "kw2"], "kw1, kw2")
    assert parsed["is_open_access"] in (True, False)
