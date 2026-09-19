"""Regressão do desmembramento de autores colapsados pelo feedparser (feeds OJS).

O item «Parsing de autores OJS possui teste de regressão» do checklist de release v1.1
(`docs/quality/RELEASE_CHECKLIST_v1.1.md` §8.4) exigia esta guarda: a heurística existe em
`app/services/article_parser.py:190-222` desde `d858451` («desmembra listas de autores
colapsadas pelo feedparser (feeds OJS)»), e até então nenhum teste a exercitava.

Cenário real (journals OJS como a Revista Perspectivas): o feedparser junta múltiplos
`<dc:creator>` repetidos numa única string `'A, B, C'` em `authors[0].name`, o que estourava
`VARCHAR(255)` em `authors` e criava um «autor» único com a lista inteira.

As asserções pinam a heurística **nos dois sentidos** — quem desmembra demais também falha:

- lista colapsada → tem de ser dividida;
- `'Sobrenome, Nome'` legítimo → NÃO pode ser dividido;
- credencial (`'Angela West, MS, BCBA'`) → NÃO pode ser dividida;
- sobrenome com «e» (`'Rocha e Silva'`) → NÃO pode ser dividido (o split é só por vírgula).
"""

from __future__ import annotations

import feedparser

from app.services.article_parser import ArticleParserService

#: Um `<dc:creator>` único cujo conteúdo é a lista inteira — a forma que o feedparser
#: produz para OJS e que `d858451` passou a desmembrar.
OJS_FEED_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Revista de teste</title>
    <item>
      <title>Artigo com autores colapsados</title>
      <link>https://exemplo.invalid/artigo/1</link>
      <dc:creator>Ana Silva, Bruno Costa, Carla Dias</dc:creator>
    </item>
  </channel>
</rss>
"""


def _authors_from_feedparser(xml: str) -> list[dict[str, str]]:
    """Extrai autores pelo caminho REAL: feedparser -> ``_extract_authors``."""
    entry = feedparser.parse(xml).entries[0]
    return ArticleParserService()._extract_authors(entry)


def test_ojs_dc_creator_colapsado_e_desmembrado_em_autores_individuais() -> None:
    """A string colapsada vira N autores — não um «autor» com a lista inteira."""
    authors = _authors_from_feedparser(OJS_FEED_XML)

    assert [a["name"] for a in authors] == ["Ana Silva", "Bruno Costa", "Carla Dias"], (
        f"a lista colapsada pelo feedparser não foi desmembrada: {authors}"
    )
    assert all(a["role"] == "author" for a in authors)


def test_nome_colapsado_nao_estoura_o_limite_da_coluna() -> None:
    """O motivo do fix: a lista inteira num único autor estourava ``VARCHAR(255)``."""
    authors = _authors_from_feedparser(OJS_FEED_XML)

    assert all(len(a["name"]) <= 255 for a in authors), (
        f"nome acima do limite da coluna: {[len(a['name']) for a in authors]}"
    )
    # O tamanho da lista é o que estourava a coluna: são 35 caracteres contra os
    # 255 do limite, então o que importa aqui é a divisão, não o comprimento.
    assert len(authors) == 3


def test_sobrenome_formato_sobrenome_virgula_nome_nao_e_dividido() -> None:
    """`'de Rose, Júlio C.'` é um autor legítimo, não uma lista de dois."""
    authors = _authors_from_feedparser(
        OJS_FEED_XML.replace("Ana Silva, Bruno Costa, Carla Dias", "de Rose, Júlio C.")
    )

    assert [a["name"] for a in authors] == ["de Rose, Júlio C."], (
        f"nome legítimo 'Sobrenome, Nome' foi dividido: {authors}"
    )


def test_credencial_nao_e_dividida_em_autores() -> None:
    """`'Angela West, MS, BCBA'` é um autor com credenciais, não três."""
    authors = _authors_from_feedparser(
        OJS_FEED_XML.replace("Ana Silva, Bruno Costa, Carla Dias", "Angela West, MS, BCBA")
    )

    assert [a["name"] for a in authors] == ["Angela West, MS, BCBA"], (
        f"credenciais foram divididas como se fossem autores: {authors}"
    )


def test_sobrenome_com_e_nao_e_dividido() -> None:
    """`'Helena de Freitas Rocha e Silva'` é UM autor — o split nunca usa « e »."""
    authors = _authors_from_feedparser(
        OJS_FEED_XML.replace(
            "Ana Silva, Bruno Costa, Carla Dias", "Helena de Freitas Rocha e Silva"
        )
    )

    assert [a["name"] for a in authors] == ["Helena de Freitas Rocha e Silva"], (
        f"sobrenome com « e » foi mutilado: {authors}"
    )


def test_lista_de_dois_nomes_completos_e_desmembrada() -> None:
    """Dois segmentos de 2+ palavras com algum de 3+ também são lista."""
    authors = _authors_from_feedparser(
        OJS_FEED_XML.replace("Ana Silva, Bruno Costa, Carla Dias", "Ana Maria Silva, Bruno Costa")
    )

    assert [a["name"] for a in authors] == ["Ana Maria Silva", "Bruno Costa"], (
        f"lista de dois nomes completos não foi desmembrada: {authors}"
    )
