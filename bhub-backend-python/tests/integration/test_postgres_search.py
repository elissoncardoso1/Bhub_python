"""Busca full-text e sugestões do ``SearchService`` contra PostgreSQL 16 real.

Task 13 / T4.2. Diferente de ``tests/test_articles.py`` (SQLite em memória, onde o
``SearchService`` cai no ramo FTS5), aqui o serviço de PRODUÇÃO roda contra o
PostgreSQL de verdade, no banco já migrado pelo caminho da Task 12
(``alembic upgrade head`` -> ``009_feed_http_cache``) e com ``search_vector``
preenchido pelo trigger da migração 008.

Cobre os cinco cenários literais do plano (português, inglês, ranking, busca
inexistente, sugestão por similaridade) e os caminhos de falha que pertencem ao
contrato: artigo não publicado fora da busca e das sugestões, query vazia/só
espaços/só pontuação sem exceção, texto com pontuação e com SQL não casando nada
nem sendo executado.

Isolamento: cada teste insere e limpa as SUAS próprias linhas controladas
(``external_id`` com o prefixo ``t13-``), então a ordem de execução em relação a
``test_migrations.py`` — que derruba e recria o schema no fim do módulo — não
importa. Zero rede.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article
from app.services.search_service import SearchService

pytestmark = pytest.mark.integration

# Prefixo de todo ``external_id`` controlado por esta suíte. É o que a limpeza
# usa para não tocar em linha alguma que não seja dela.
CONTROLLED_PREFIX = "t13-"

SUITE_DATE = datetime(2025, 6, 1, tzinfo=UTC)

# --- Conjunto canônico: um artigo em português, um em inglês, um não publicado ---
#
# Os termos são deliberadamente raros ("cerrado", "machine translation") para que
# cada query tenha um casamento inequívoco e a asserção possa ser de IGUALDADE,
# não de pertinência.
PT_EXTERNAL_ID = f"{CONTROLLED_PREFIX}pt-cerrado"
PT_TITLE = "Agricultura de precisão no cerrado brasileiro"
PT_ABSTRACT = "Sensores remotos medem a produtividade agrícola no bioma cerrado."
PT_QUERY = "cerrado"

EN_EXTERNAL_ID = f"{CONTROLLED_PREFIX}en-mt"
EN_TITLE = "Machine translation for low resource languages"
EN_ABSTRACT = "A deep learning approach to machine translation without parallel corpora."
EN_QUERY = "machine translation"
# Termo que SÓ casa pelo ``to_tsvector('english', …)`` que o trigger da 008 soma
# ao português: o stemmer português guarda "learning" e não produz o lexema
# ``learn`` (medido no PostgreSQL real). ``EN_QUERY`` sozinho casa também pela
# vectorização só-portuguesa, então é este termo que prende o ingrediente
# bilíngue (Task 13.E, achado F2 da revisão independente).
EN_ENGLISH_VECTOR_ONLY_TERM = "learn"

UNPUBLISHED_EXTERNAL_ID = f"{CONTROLLED_PREFIX}unpublished"
UNPUBLISHED_TITLE = "Cerrado: revisão sistemática ainda não publicada"
UNPUBLISHED_ABSTRACT = "Manuscrito sobre o cerrado que ainda não foi publicado."
# Query que casa SÓ o artigo não publicado, pelo título dele.
UNPUBLISHED_ONLY_QUERY = "revisão sistemática"

# --- Par de ranking: mesma query, pesos diferentes ------------------------------
#
# O forte carrega o termo no TÍTULO (peso A do trigger da 008); o fraco só no
# RESUMO (peso B). O forte é o MAIS ANTIGO de propósito: o desempate do serviço é
# ``publication_date desc`` depois do rank, então a ordem só pode vir do rank.
RANK_STRONG_EXTERNAL_ID = f"{CONTROLLED_PREFIX}rank-strong"
RANK_STRONG_TITLE = "Manejo do cerrado e produtividade agrícola"
RANK_STRONG_ABSTRACT = "Cobertura vegetal e estoque de carbono no solo."
RANK_STRONG_DATE = datetime(2024, 1, 1, tzinfo=UTC)

RANK_WEAK_EXTERNAL_ID = f"{CONTROLLED_PREFIX}rank-weak"
RANK_WEAK_TITLE = "Modelagem estatística de safras no centro-oeste"
RANK_WEAK_ABSTRACT = "O estudo cobre o cerrado e a expansão da soja na região."
RANK_WEAK_DATE = datetime(2026, 1, 1, tzinfo=UTC)

# --- Par de similaridade: títulos distintos casando o mesmo fragmento -----------
#
# Um título é EXATAMENTE o fragmento (``similarity`` = 1.0); o outro o contém
# dentro de uma frase longa (similaridade baixa). A ordem esperada vem daí.
#
# O título MENOS similar começa com "A" de propósito (Task 13.E, achado F1 da
# revisão independente): sem ``ORDER BY`` o ``SELECT DISTINCT`` do PostgreSQL já
# devolve as linhas ordenadas por título — o plano é ``Unique -> Sort`` com
# ``Sort Key: title`` —, então a ordem alfabética destes dois títulos
# ["Acompanhamento…", "Cerrado"] é o CONTRÁRIO da ordem por similaridade. Se o
# ``ORDER BY similarity(...) DESC`` do serviço sumir, a asserção de ordem falha
# em vez de passar por coincidência com a ordem alfabética.
SIMILAR_EXACT_EXTERNAL_ID = f"{CONTROLLED_PREFIX}similar-exact"
SIMILAR_EXACT_TITLE = "Cerrado"
SIMILAR_LONG_EXTERNAL_ID = f"{CONTROLLED_PREFIX}similar-long"
SIMILAR_LONG_TITLE = "Acompanhamento do cerrado por satélite"
SIMILAR_QUERY = "cerrado"


def _article(
    external_id: str,
    title: str,
    abstract: str,
    *,
    language: str = "en",
    is_published: bool = True,
    publication_date: datetime = SUITE_DATE,
) -> Article:
    """Monta uma linha controlada. ``search_vector`` NÃO é setado de propósito.

    A coluna é preenchida pelo trigger ``articles_search_vector_trigger`` da
    migração 008 no INSERT; se ela ficasse nula, a busca não casaria nada e os
    testes abaixo mediriam o vazio em vez do comportamento real.
    """
    return Article(
        external_id=external_id,
        title=title,
        abstract=abstract,
        language=language,
        is_published=is_published,
        publication_date=publication_date,
        journal_name="Periódico de Teste 13",
    )


async def _purge_controlled_articles(session: AsyncSession) -> None:
    """Apaga só as linhas desta suíte (``external_id`` com o prefixo ``t13-``)."""
    stmt = delete(Article).where(Article.external_id.like(f"{CONTROLLED_PREFIX}%"))
    await session.execute(stmt.execution_options(synchronize_session=False))
    await session.commit()


async def _insert_controlled(session: AsyncSession, articles: list[Article]) -> None:
    session.add_all(articles)
    await session.commit()


@pytest_asyncio.fixture
async def article_session(pg_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Sessão contra o banco migrado, sem nenhuma linha controlada de outro teste."""
    await _purge_controlled_articles(pg_session)
    yield pg_session
    # Só limpeza: uma falha aqui (inclusive transação abortada por uma asserção
    # que falhou no meio) nunca pode substituir o erro real do teste.
    try:
        await pg_session.rollback()
        await _purge_controlled_articles(pg_session)
    except Exception as exc:  # só alcançável quando o teardown falha; tests/ fora do --cov=app
        print(f"AVISO: limpeza pós-teste falhou: {exc!r}")


@pytest_asyncio.fixture
async def canonical_articles(article_session: AsyncSession) -> AsyncSession:
    """Um artigo publicado em português, um em inglês e um NÃO publicado."""
    await _insert_controlled(
        article_session,
        [
            _article(PT_EXTERNAL_ID, PT_TITLE, PT_ABSTRACT, language="pt"),
            _article(EN_EXTERNAL_ID, EN_TITLE, EN_ABSTRACT, language="en"),
            _article(
                UNPUBLISHED_EXTERNAL_ID,
                UNPUBLISHED_TITLE,
                UNPUBLISHED_ABSTRACT,
                language="pt",
                is_published=False,
            ),
        ],
    )
    return article_session


@pytest_asyncio.fixture
async def ranking_articles(article_session: AsyncSession) -> AsyncSession:
    """Dois artigos publicados casando ``cerrado`` com relevância bem diferente."""
    await _insert_controlled(
        article_session,
        [
            _article(
                RANK_STRONG_EXTERNAL_ID,
                RANK_STRONG_TITLE,
                RANK_STRONG_ABSTRACT,
                language="pt",
                publication_date=RANK_STRONG_DATE,
            ),
            _article(
                RANK_WEAK_EXTERNAL_ID,
                RANK_WEAK_TITLE,
                RANK_WEAK_ABSTRACT,
                language="pt",
                publication_date=RANK_WEAK_DATE,
            ),
        ],
    )
    return article_session


@pytest_asyncio.fixture
async def similarity_articles(article_session: AsyncSession) -> AsyncSession:
    """Dois títulos publicados contendo ``cerrado``, com similaridade bem diferente."""
    await _insert_controlled(
        article_session,
        [
            _article(
                SIMILAR_EXACT_EXTERNAL_ID, SIMILAR_EXACT_TITLE, "Resumo curto.", language="pt"
            ),
            _article(
                SIMILAR_LONG_EXTERNAL_ID,
                SIMILAR_LONG_TITLE,
                "Resumo sobre observação da terra.",
                language="pt",
            ),
            _article(
                UNPUBLISHED_EXTERNAL_ID,
                UNPUBLISHED_TITLE,
                UNPUBLISHED_ABSTRACT,
                language="pt",
                is_published=False,
            ),
        ],
    )
    return article_session


# --- Precondição: o trigger da 008 preenche search_vector no INSERT --------------


async def test_search_vector_is_populated_by_the_insert_trigger(
    canonical_articles: AsyncSession,
) -> None:
    vector = await canonical_articles.scalar(
        text("SELECT search_vector FROM articles WHERE external_id = :eid"),
        {"eid": PT_EXTERNAL_ID},
    )
    assert vector, "o trigger da 008 deveria ter preenchido search_vector no INSERT"
    # O vetor guarda o ``to_tsvector('english', title)`` junto do português, então
    # o próprio termo aparece como lexema mesmo sem stemming nenhum.
    assert "cerrado" in str(vector)


# --- 1. Português ---------------------------------------------------------------


async def test_portuguese_query_returns_the_controlled_article(
    canonical_articles: AsyncSession,
) -> None:
    results = await SearchService(canonical_articles).search(PT_QUERY)

    assert [article.title for article in results] == [PT_TITLE]
    assert results[0].language == "pt"


# --- 2. Inglês ------------------------------------------------------------------


async def test_english_query_returns_the_controlled_article(
    canonical_articles: AsyncSession,
) -> None:
    service = SearchService(canonical_articles)

    results = await service.search(EN_QUERY)

    assert [article.title for article in results] == [EN_TITLE]
    assert results[0].language == "en"

    # O ingrediente, não só o resultado: este termo NÃO existe no vetor
    # só-português desta fixture (o português guarda ``learning``, não ``learn``),
    # então ele só casa porque o trigger da 008 grava a vectorização ``english``
    # junto da portuguesa. Apagar os dois ``to_tsvector('english', …)`` do trigger
    # faz esta busca devolver vazio.
    english_only = await service.search(EN_ENGLISH_VECTOR_ONLY_TERM)
    assert [article.title for article in english_only] == [EN_TITLE]


# --- 3. Ranking -----------------------------------------------------------------


async def test_ranking_puts_the_title_match_first(ranking_articles: AsyncSession) -> None:
    """Ordem, não pertinência: o título (peso A) vem antes do resumo (peso B)."""
    titles = [article.title for article in await SearchService(ranking_articles).search(PT_QUERY)]

    assert titles == [RANK_STRONG_TITLE, RANK_WEAK_TITLE], (
        f"o artigo com o termo no TÍTULO deveria vir primeiro; ordem observada: {titles!r}"
    )


# --- 4. Busca inexistente / vazia ----------------------------------------------


async def test_nonsense_query_returns_empty(canonical_articles: AsyncSession) -> None:
    assert await SearchService(canonical_articles).search("zxqwvbnmplkj") == []


async def test_stopwords_only_query_returns_empty(canonical_articles: AsyncSession) -> None:
    service = SearchService(canonical_articles)

    assert await service.search("de da do para com") == []
    assert await service.search("a o e de") == []


async def test_empty_and_blank_queries_return_empty(canonical_articles: AsyncSession) -> None:
    service = SearchService(canonical_articles)

    for query in ("", "   ", "\t\n  ", "!!!", "--- ... ---"):
        assert await service.search(query) == [], f"query vazia/sem termo: {query!r}"


# --- Caminhos de falha do contrato ---------------------------------------------


async def test_unpublished_article_is_excluded_from_search(
    canonical_articles: AsyncSession,
) -> None:
    """Query que casaria SÓ o não publicado devolve vazio, sem levantar."""
    service = SearchService(canonical_articles)

    assert await service.search(UNPUBLISHED_ONLY_QUERY) == []
    # Sanidade: os publicados continuam alcançáveis na mesma sessão.
    assert [a.title for a in await service.search(PT_QUERY)] == [PT_TITLE]


async def test_unsafe_query_text_does_not_raise_and_matches_nothing(
    canonical_articles: AsyncSession,
) -> None:
    """Pontuação e SQL não levantam, não casam nada e não são EXECUTADOS."""
    service = SearchService(canonical_articles)

    for query in (
        "'; DROP TABLE articles; --",
        '" OR 1=1 --',
        "cerrado; DELETE FROM articles",
        "state-of-the-art",
        "%%%___",
    ):
        assert await service.search(query) == [], f"query insegura casou algo: {query!r}"

    # A tabela continua de pé e a busca normal continua respondendo: nada rodou.
    assert [a.title for a in await service.search(PT_QUERY)] == [PT_TITLE]


# --- 5. Sugestão por similaridade ----------------------------------------------
#
# CONTRATO: ``get_suggestions`` devolve os títulos PUBLICADOS que contêm o
# fragmento, sem levantar. O ramo PostgreSQL montava
# ``SELECT DISTINCT title ... ORDER BY similarity(title, query)``, que o
# PostgreSQL recusa (InvalidColumnReferenceError); o ramo SQLite não faz esse
# ORDER BY e por isso nenhum teste unitário pega o defeito.


async def test_suggestions_return_titles_containing_the_fragment(
    canonical_articles: AsyncSession,
) -> None:
    suggestions = await SearchService(canonical_articles).get_suggestions(SIMILAR_QUERY)

    assert suggestions == [PT_TITLE]


async def test_suggestions_with_a_fragment_matching_nothing_return_empty(
    canonical_articles: AsyncSession,
) -> None:
    service = SearchService(canonical_articles)

    assert await service.get_suggestions("zxqwvbnmplkj") == []
    assert await service.suggest("zxqwvbnmplkj") == []


async def test_suggestions_ignore_fragments_shorter_than_two_characters(
    canonical_articles: AsyncSession,
) -> None:
    service = SearchService(canonical_articles)

    assert await service.get_suggestions("c") == []
    assert await service.get_suggestions("") == []


async def test_suggestions_exclude_unpublished_titles(canonical_articles: AsyncSession) -> None:
    suggestions = await SearchService(canonical_articles).get_suggestions("não publicada")

    assert suggestions == []


async def test_suggestions_order_the_most_similar_title_first(
    similarity_articles: AsyncSession,
) -> None:
    suggestions = await SearchService(similarity_articles).get_suggestions(SIMILAR_QUERY)

    assert suggestions == [SIMILAR_EXACT_TITLE, SIMILAR_LONG_TITLE], (
        "o título mais parecido com o fragmento deveria vir primeiro; "
        f"ordem observada: {suggestions!r}"
    )
