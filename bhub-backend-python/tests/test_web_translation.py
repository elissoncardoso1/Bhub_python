"""
Testes do endpoint HTMX POST /translate (tradução do resumo de um artigo).
"""

import json
from html.parser import HTMLParser

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import manager as ai_manager_module
from app.ai.manager import MAX_OUTPUT_TOKENS, AIProvider, DeepSeekService
from app.core.limiter import limiter
from app.models import Article
from app.models.translation_cache import TranslationCache
from app.web import translation as translation_module

ABSTRACT = "Reinforcement schedules shape operant behavior."


class FakeAIManager:
    def __init__(self, result):
        self.result = result
        self.calls: list[str] = []

    async def translate(self, text, target_lang="pt"):  # noqa: ARG002
        self.calls.append(text)
        return self.result


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def fake_ai(monkeypatch):
    def install(result):
        fake = FakeAIManager(result)
        monkeypatch.setattr(translation_module, "get_ai_manager", lambda: fake)
        return fake

    return install


async def _article(db: AsyncSession, abstract: str | None = ABSTRACT) -> Article:
    article = Article(title="T", abstract=abstract, is_published=True, language="en")
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


class _HxValsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hx_vals = None

    def handle_starttag(self, tag, attrs):  # noqa: ARG002
        attrs = dict(attrs)
        if attrs.get("hx-post") == "/translate":
            self.hx_vals = attrs.get("hx-vals")


@pytest.mark.asyncio
async def test_botao_envia_hx_vals_json_valido(client: AsyncClient, db_session: AsyncSession):
    # Regressão: hx-vals entre aspas duplas quebrava no 1º `"` do JSON e o htmx enviava {}.
    article = await _article(db_session, abstract="Text with \"quotes\" and 'apostrophes'.")
    response = await client.get(f"/articles/{article.id}")
    assert response.status_code == 200

    parser = _HxValsParser()
    parser.feed(response.text)
    assert json.loads(parser.hx_vals) == {
        "element_id": "abstract-content",
        "article_id": article.id,
    }


@pytest.mark.asyncio
async def test_traduz_abstract_do_banco_e_ignora_texto_do_cliente(
    client: AsyncClient, db_session: AsyncSession, fake_ai
):
    article = await _article(db_session)
    fake = fake_ai(("Esquemas de reforço moldam o comportamento operante.", AIProvider.DEEPSEEK))

    response = await client.post(
        "/translate", json={"article_id": article.id, "text": "Hello world, test"}
    )

    assert response.status_code == 200
    assert "Esquemas de refor" in response.text
    assert fake.calls == [ABSTRACT]
    await db_session.refresh(article)
    assert article.abstract_translated == "Esquemas de reforço moldam o comportamento operante."


@pytest.mark.asyncio
async def test_falha_de_todos_provedores_nao_grava_nada(
    client: AsyncClient, db_session: AsyncSession, fake_ai
):
    article = await _article(db_session)
    fake_ai((ABSTRACT, None))  # contrato do AIManager quando todos falham

    response = await client.post("/translate", json={"article_id": article.id})

    assert response.status_code == 200
    assert "Tradução indisponível" in response.text
    assert ABSTRACT in response.text  # resumo original continua visível
    assert "hx-swap-oob" not in response.text  # botão continua disponível para nova tentativa
    await db_session.refresh(article)
    assert article.abstract_translated is None
    cache = (await db_session.execute(select(TranslationCache))).scalars().all()
    assert cache == []


@pytest.mark.asyncio
async def test_artigo_inexistente_nao_chama_ia(client: AsyncClient, fake_ai):
    fake = fake_ai(("x", AIProvider.DEEPSEEK))

    response = await client.post("/translate", json={"article_id": 999999})

    assert response.status_code == 200
    assert "Resumo não disponível" in response.text
    assert fake.calls == []


@pytest.mark.asyncio
async def test_sem_article_id_e_rejeitado(client: AsyncClient, fake_ai):
    fake = fake_ai(("x", AIProvider.DEEPSEEK))

    response = await client.post("/translate", json={"text": "qualquer texto"})

    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.asyncio
async def test_rate_limit_por_minuto(client: AsyncClient, fake_ai):
    fake_ai(("x", AIProvider.DEEPSEEK))

    statuses = [
        (await client.post("/translate", json={"article_id": 999999})).status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


@pytest.mark.asyncio
async def test_deepseek_limita_max_tokens(monkeypatch):
    sent = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers, json):  # noqa: ARG002
            sent.update(json)
            return FakeResponse()

    monkeypatch.setattr(ai_manager_module.httpx, "AsyncClient", FakeClient)
    service = DeepSeekService()

    await service.translate("a" * 5000)
    assert sent["max_tokens"] == MAX_OUTPUT_TOKENS

    await service.translate("a" * 100)
    assert sent["max_tokens"] == 200
