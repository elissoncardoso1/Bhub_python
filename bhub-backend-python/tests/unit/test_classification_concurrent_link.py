"""Guard ESTREITO da corrida do vínculo artigo↔categoria (Task 14, finding F4).

O milestone 14.C consertou a corrida de dois dispatches do MESMO artigo
(``tests/integration/test_arq_worker.py::test_dois_dispatches_concorrentes_do_mesmo_artigo_nao_quebram_o_job``)
tratando ``IntegrityError`` no INSERT de ``article_categories``. Aquele
``except`` era LARGO: engolia QUALQUER violação de integridade naquele INSERT —
FK, NOT NULL, outra unique — não só a colisão alvo ``uq_article_category``.
O sinal de erro se perdia (finding F4 do review do 14.F).

Estes dois testes prendem as DUAS direções da propriedade, no dialeto em que a
suíte unitária roda (SQLite/aiosqlite):

1. ``test_violacao_de_integridade_nao_alvo_propaga`` — uma violação de
   integridade que NÃO é a colisão alvo precisa ESCAPAR de
   ``assign_categories_to_article``. Violação REAL do driver
   (``sqlite3.IntegrityError`` de NOT NULL), não um ``Exception`` de mentira.
2. ``test_corrida_do_vinculo_alvo_e_recuperada`` — a corrida ALVO continua
   recuperável: o perdedor não levanta nada e o vínculo fica único.

NOT NULL é o caso não-alvo alcançável no dialeto unitário. A violação de FK —
a que a produção de fato alcança, quando a linha do artigo some entre o SELECT
e o INSERT — é medida no módulo de integração, porque o SQLite só a levanta com
``PRAGMA foreign_keys=ON``, que a engine de teste não liga (medido no A4 do
milestone 14.G; ver o relatório da task).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Category, article_categories
from app.services.classification_service import ClassificationService

SLUG = "t14g-guard"


class _VinculoAusente:
    """Resultado do SELECT do check-then-act no instante em que ESTE job leu.

    Só ``first()`` é usado pelo código de produção nessa consulta.
    """

    @staticmethod
    def first() -> None:
        return None


def _e_o_select_do_vinculo(statement: Any) -> bool:
    """Identifica ESTRUTURALMENTE o SELECT do vínculo (sem olhar o texto do SQL)."""
    if not getattr(statement, "is_select", False):
        return False
    origens_declaradas = getattr(statement, "get_final_froms", None)
    if not callable(origens_declaradas):
        return False
    origens = origens_declaradas()
    if not isinstance(origens, Iterable):
        return False
    return any(getattr(origem, "name", None) == article_categories.name for origem in origens)


class _SessaoComCorrida:
    """Sessão real com a janela da corrida: o check-then-act lê ANTES do INSERT.

    Encaminha tudo para a sessão real; só o SELECT do vínculo responde "não
    existe", que é o que o SELECT devolveu de verdade quando o outro job ainda
    não tinha commitado. O INSERT executado é o de PRODUÇÃO.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._corrida_pendente = True
        # Contador para o teste NÃO poder passar sem a janela: se o matcher
        # ``_e_o_select_do_vinculo`` deixar de casar (mudança no statement, no
        # dialeto ou no nome da tabela), o SELECT real devolveria o vínculo,
        # o código cairia no ``continue`` sequencial e as asserções continuariam
        # verdes sem exercitar o conflito nenhuma vez. O teste asserta == 1
        # (o wrapper intercepta no máximo uma vez e há uma categoria ⇒ um SELECT).
        self.interceptacoes = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        if self._corrida_pendente and _e_o_select_do_vinculo(statement):
            self._corrida_pendente = False
            self.interceptacoes += 1
            return _VinculoAusente()
        return await self._session.execute(statement, *args, **kwargs)


async def _artigo_e_categoria(db_session: AsyncSession) -> tuple[int, int]:
    article = Article(
        external_id="t14g-guard-article",
        title="Artigo do guard",
        abstract="Texto de teste.",
        keywords="",
        language="pt",
        is_published=True,
    )
    category = Category(name="Guard", slug=SLUG, description="categoria do guard")
    db_session.add_all([article, category])
    await db_session.commit()
    return article.id, category.id


async def test_violacao_de_integridade_nao_alvo_propaga(db_session: AsyncSession) -> None:
    """Uma violação REAL que não é ``uq_article_category`` precisa ESCAPAR.

    ``article_id=None`` viola o NOT NULL de ``article_categories.article_id`` —
    o mesmo veredito que a FK recebe em produção (23502 / 23503, ambos
    propagam). Com o ``except IntegrityError`` largo do 14.C a função engolia o
    erro e devolvia ``[]``, escondendo a violação.
    """
    category = Category(name="Guard", slug=SLUG, description="categoria do guard")
    db_session.add(category)
    await db_session.commit()

    # ``None`` de propósito (por isso ``Any``): é o que faz o DRIVER levantar o
    # NOT NULL real. A produção nunca passa ``None`` — o alvo aqui é medir um
    # erro REAL de integridade que não é a colisão alvo.
    article_id_que_viola_o_not_null: Any = None

    try:
        with pytest.raises(IntegrityError):
            await ClassificationService.assign_categories_to_article(
                db=db_session,
                article_id=article_id_que_viola_o_not_null,
                category_slugs_with_confidence=[(SLUG, 0.9)],
                auto_create=True,
            )
    finally:
        await db_session.rollback()


async def test_corrida_do_vinculo_alvo_e_recuperada(db_session: AsyncSession) -> None:
    """A corrida ALVO continua recuperável: perdedor não levanta e o vínculo é único.

    O vínculo é inserido de verdade ANTES (é o "outro job comitando dentro da
    janela" do check-then-act) e o SELECT do vínculo é o único que mente: ele
    devolve o estado lido no instante anterior ao commit do outro job.
    """
    article_id, category_id = await _artigo_e_categoria(db_session)
    await db_session.execute(
        insert(article_categories).values(
            article_id=article_id,
            category_id=category_id,
            confidence=0.9,
            is_primary=True,
            auto_created=False,
        )
    )
    await db_session.commit()

    sessao_com_corrida = _SessaoComCorrida(db_session)
    atribuidas = await ClassificationService.assign_categories_to_article(
        db=sessao_com_corrida,
        article_id=article_id,
        category_slugs_with_confidence=[(SLUG, 0.9)],
        auto_create=True,
    )
    assert sessao_com_corrida.interceptacoes == 1, (
        "o SELECT do vínculo não foi interceptado: sem a janela da corrida este "
        "teste deixaria de exercitar o caminho do conflito alvo e passaria verde "
        f"sem provar nada (interceptações={sessao_com_corrida.interceptacoes})"
    )

    vinculos = (
        await db_session.execute(
            select(article_categories).where(article_categories.c.article_id == article_id)
        )
    ).all()
    assert atribuidas == [], "o perdedor da corrida não deve reportar o vínculo como novo"
    assert len(vinculos) == 1, f"a corrida duplicou o vínculo artigo↔categoria: {vinculos}"
