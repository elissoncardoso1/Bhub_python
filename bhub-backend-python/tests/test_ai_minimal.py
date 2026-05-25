import json

import pytest

from app.ai.local_llm_service import LocalLLMService
from app.ai.model_manager import ModelManager
from app.services.article_parser import ArticleParserService


def test_model_manager_custom_path(monkeypatch, tmp_path):
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_text("fake")

    monkeypatch.setattr("app.ai.model_manager.settings.local_llm_model_path", str(dummy_model))
    mm = ModelManager()

    path = mm.get_model_path()
    assert path == dummy_model


def test_model_manager_unsupported_model(monkeypatch):
    monkeypatch.setattr("app.ai.model_manager.settings.local_llm_model_name", "unknown-model")
    mm = ModelManager()
    assert mm.get_model_path() is None


@pytest.mark.asyncio
async def test_local_llm_classify_with_dummy_llm(monkeypatch):
    dummy_llm = lambda *args, **kwargs: {
        "choices": [{"text": json.dumps({"category": "clinica", "confidence": 0.9})}]
    }
    monkeypatch.setattr(LocalLLMService, "_get_llm", lambda self: dummy_llm)

    service = LocalLLMService()
    category, confidence = await service.classify("Titulo\nResumo")
    assert category == "clinica"
    assert confidence == pytest.approx(0.9, rel=1e-3)


@pytest.mark.asyncio
async def test_local_llm_classify_multiple_with_dummy_llm(monkeypatch):
    dummy_llm = lambda *args, **kwargs: {
        "choices": [
            {
                "text": json.dumps(
                    {"categories": [{"slug": "educacao", "confidence": 0.8}]}
                )
            }
        ]
    }
    monkeypatch.setattr(LocalLLMService, "_get_llm", lambda self: dummy_llm)

    service = LocalLLMService()
    categories = await service.classify_multiple("Titulo\nResumo")
    assert categories == [("educacao", 0.8)]


def test_article_parser_generate_and_parse_entry():
    parser = ArticleParserService()

    entry = {
        "id": "abc123",
        "title": "Sample Title",
        "abstract": "Resumo do artigo",
        "link": "https://example.com/article",
        "published": "2024-01-01",
        "authors": [{"name": "Alice"}],
        "tags": [{"term": "tag1"}, {"term": "tag2"}],
    }

    external_id = parser.generate_external_id(entry, feed_id=1)
    assert external_id.startswith("feed_1_")

    parsed = parser.parse_entry(entry, journal_name="Journal X")
    assert parsed["title"] == "Sample Title"
    assert parsed.get("abstract") in (None, "Resumo do artigo")
    assert parsed["url"] == "https://example.com/article"
    assert parsed.get("journal") in (None, "Journal X")
    assert parsed.get("keywords") in (["tag1", "tag2"], "tag1, tag2")
