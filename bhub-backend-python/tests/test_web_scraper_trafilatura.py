"""Testes do fallback trafilatura na extração de artigos."""

from app.services.web_scraper import WebScrapingService

HTML_SEM_META = """
<html><head><title>Página</title></head><body>
<div id="conteudo">
<h1>Efeitos do reforçamento diferencial em contexto clínico</h1>
<p>Este estudo investigou os efeitos do reforçamento diferencial de comportamentos
alternativos em um contexto clínico com participantes diagnosticados com TEA.
Os resultados indicaram redução consistente de comportamentos-problema.</p>
<p>Foram conduzidas três fases experimentais com delineamento de linha de base
múltipla entre participantes, com medidas repetidas de frequência e duração.
A integridade do procedimento foi avaliada em todas as sessões experimentais.</p>
<p>Discutem-se implicações para a prática clínica baseada em evidências e
limitações metodológicas do delineamento adotado neste estudo.</p>
</div>
</body></html>
"""


def test_fallback_preenche_abstract_quando_seletores_falham():
    service = WebScrapingService()
    data = {
        "title": "Sem título",
        "abstract": None,
        "authors": [],
    }
    service._apply_trafilatura_fallback(HTML_SEM_META, data)
    assert data["abstract"] is not None
    assert "reforçamento diferencial" in data["abstract"]
    assert data["title"] != "Sem título"


def test_fallback_nao_sobrescreve_dados_existentes():
    service = WebScrapingService()
    data = {
        "title": "Título original",
        "abstract": "Abstract original",
        "authors": [{"name": "Autora"}],
    }
    service._apply_trafilatura_fallback(HTML_SEM_META, data)
    assert data["title"] == "Título original"
    assert data["abstract"] == "Abstract original"
    assert data["authors"] == [{"name": "Autora"}]
