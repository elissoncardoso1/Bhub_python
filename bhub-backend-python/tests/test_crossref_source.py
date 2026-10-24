"""Testes do adaptador Crossref (sem rede — HTTP mockado)."""

import json
from datetime import datetime

import httpx
import pytest

from app.services.crossref_source import (
    CrossrefSource,
    work_to_entry,
)

JABA_WORK = {
    "DOI": "10.1002/JABA.70077",
    "title": ["Parametric evaluation of procedural fidelity"],
    "author": [
        {"given": "Paige", "family": "O'Neill"},
        {"given": "Catalina N.", "family": "Rey"},
    ],
    "published": {"date-parts": [[2026, 8, 17]]},
    "container-title": ["Journal of Applied Behavior Analysis"],
    "abstract": (
        "<jats:title>Abstract</jats:title><jats:p>Differential <jats:italic>reinforcement"
        "</jats:italic> was evaluated.</jats:p>"
    ),
    "URL": "https://doi.org/10.1002/jaba.70077",
    "type": "journal-article",
    "license": [{"URL": "http://onlinelibrary.wiley.com/termsAndConditions"}],
}


def make_source(handler) -> CrossrefSource:
    transport = httpx.MockTransport(handler)
    return CrossrefSource(client=httpx.AsyncClient(transport=transport))


def works_response(items: list[dict]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"status": "ok", "message": {"items": items, "total-results": len(items)}},
        headers={"Content-Type": "application/json"},
    )


# --- Conversão de um work para entrada do feedparser -----------------------


def test_work_vira_entrada_no_formato_do_feedparser():
    entry = work_to_entry(JABA_WORK)

    assert entry is not None
    assert entry["id"] == "doi:10.1002/jaba.70077"
    assert entry["title"] == "Parametric evaluation of procedural fidelity"
    assert entry["published"] == "2026-08-17"
    assert entry["journal"] == "Journal of Applied Behavior Analysis"
    assert entry["link"] == "https://doi.org/10.1002/jaba.70077"
    assert entry["authors"] == [{"name": "Paige O'Neill"}, {"name": "Catalina N. Rey"}]


def test_doi_e_normalizado_e_semente_do_id():
    """DOI em caixa alta não pode gerar um segundo artigo para o mesmo trabalho."""
    entry = work_to_entry({**JABA_WORK, "DOI": "10.1002/JABA.70077"})
    assert entry is not None
    assert entry["id"] == "doi:10.1002/jaba.70077"
    assert entry["doi"] == "10.1002/jaba.70077"


def test_doi_com_prefixo_de_url_e_normalizado():
    entry = work_to_entry({**JABA_WORK, "DOI": "https://doi.org/10.1002/JABA.1"})
    assert entry is not None
    assert entry["doi"] == "10.1002/jaba.1"


def test_abstract_jats_e_limpo():
    """Tags JATS não podem vazar para o resumo — o parser só conhece HTML."""
    entry = work_to_entry(JABA_WORK)
    assert entry is not None
    assert entry["summary"] == "Abstract Differential reinforcement was evaluated."
    assert "jats" not in entry["summary"]


def test_sem_doi_ou_sem_titulo_e_descartado():
    assert work_to_entry({"title": ["T"], "DOI": None}) is None
    assert work_to_entry({"title": [], "DOI": "10.1/x"}) is None
    assert work_to_entry({"title": [""], "DOI": "10.1/x"}) is None


def test_correction_to_e_descartado():
    """Correções vêm como journal-article e poluiriam a listagem.

    As formas abaixo foram medidas no Crossref em 2026-09-25 (ver
    ``scripts/probe_corrections.py``).
    """
    descartar = [
        "Correction: POWER: A Caregiver Implemented Mand Training Intervention",
        "Correction to: Big Surprises: Jackpot Reinforcers in Research",
        "Correction to ‘Antecedent interventions for pediatric feeding problems’",
        "Correction to “Improving undergraduate students' email etiquette”",
        "Erratum: Some study",
        "Retraction: Some study",
        "Corrigendum: Some study",
    ]
    for title in descartar:
        assert work_to_entry({**JABA_WORK, "title": [title]}) is None, title


def test_titulo_legitimo_com_a_palavra_correction_nao_e_descartado():
    """Sem o delimitador, o título é conteúdo real — medido no corpus atual."""
    manter = [
        "Correction to behavior is possible",
        "The Performance Diagnostic Checklist—Human Services: a Correction",
        "EFFECTS OF IMMEDIATE SELF‐CORRECTION, DELAYED SELF‐CORRECTION ON TASK",
        "Transitioning from rich to lean reinforcement as a form of error correction",
        "AN ANALYSIS OF ERROR‐CORRECTION PROCEDURES DURING DISCRIMINATION TRAINING",
    ]
    for title in manter:
        assert work_to_entry({**JABA_WORK, "title": [title]}) is not None, title


def test_data_truncada_e_completada_com_dia_1():
    """Crossref deposita datas imprecisas: só ano ou ano+mês."""
    only_year = work_to_entry({**JABA_WORK, "published": {"date-parts": [[2015]]}})
    assert only_year is not None and only_year["published"] == "2015-01-01"

    year_month = work_to_entry({**JABA_WORK, "published": {"date-parts": [[2026, 8]]}})
    assert year_month is not None and year_month["published"] == "2026-08-01"

    assert work_to_entry({**JABA_WORK, "published": {}})["published"] is None


def test_data_fora_de_faixa_degrada_para_o_ano():
    """Dado ruim da editora (mês 13) não pode derrubar a ingestão."""
    entry = work_to_entry({**JABA_WORK, "published": {"date-parts": [[2026, 13]]}})
    assert entry is not None and entry["published"] == "2026-01-01"


def test_autor_sem_family_usa_name():
    entry = work_to_entry({**JABA_WORK, "author": [{"name": "Grupo de Pesquisa X"}]})
    assert entry is not None
    assert entry["authors"] == [{"name": "Grupo de Pesquisa X"}]


def test_sem_pdf_url_no_mapeamento():
    """O link do Crossref aponta para a editora bloqueada; não deve virar pdf_url."""
    entry = work_to_entry(JABA_WORK)
    assert entry is not None
    assert "pdf_url" not in entry


def test_open_access_exige_licenca_cc_explicita():
    """O detector do parser procura "creative commons"; a URL não casa sozinha."""
    from app.services.article_parser import ArticleParserService

    parser = ArticleParserService()
    cc = work_to_entry(
        {**JABA_WORK, "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}]}
    )
    assert cc is not None
    assert parser._detect_open_access(cc) is True

    zero = work_to_entry(
        {**JABA_WORK, "license": ["https://creativecommons.org/publicdomain/zero/1.0/"]}
    )
    assert zero is not None
    assert parser._detect_open_access(zero) is True

    # Termos de uso da editora não são acesso aberto.
    paid = work_to_entry(
        {**JABA_WORK, "license": [{"URL": "http://onlinelibrary.wiley.com/termsAndConditions"}]}
    )
    assert paid is not None
    assert parser._detect_open_access(paid) is False

    # Sem licença nenhuma também não.
    assert parser._detect_open_access(work_to_entry(JABA_WORK)) is False


# --- Fetch com paginação --------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_works_retorna_entradas_e_classifica_ok():
    source = make_source(lambda _r: works_response([JABA_WORK]))
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "ok"
    entries = json.loads(result.text)["entries"]
    assert len(entries) == 1
    assert entries[0]["id"] == "doi:10.1002/jaba.70077"


@pytest.mark.asyncio
async def test_janela_inicial_e_de_90_dias():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return works_response([])

    source = make_source(handler)
    try:
        await source.fetch_works(
            "1938-3703",
            last_successful_sync_at=None,
            now=datetime(2026, 9, 25, 12, 0, 0),
        )
    finally:
        await source.close()

    assert "from-pub-date:2026-06-27" in seen["filter"]
    assert "until-pub-date:2026-09-25" in seen["filter"]
    assert "type:journal-article" in seen["filter"]


@pytest.mark.asyncio
async def test_janela_incremental_e_de_7_dias():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return works_response([])

    source = make_source(handler)
    try:
        await source.fetch_works(
            "1938-3703",
            last_successful_sync_at=datetime(2026, 9, 24),
            now=datetime(2026, 9, 25, 12, 0, 0),
        )
    finally:
        await source.close()

    assert "from-pub-date:2026-09-18" in seen["filter"]


@pytest.mark.asyncio
async def test_pagina_ate_esgotar_e_nao_passa_do_teto():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", 0))
        calls.append(offset)
        # Sempre devolve a página cheia: força o teto de páginas.
        return works_response([{**JABA_WORK, "DOI": f"10.1/x{offset}-{i}"} for i in range(100)])

    source = make_source(handler)
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert calls == [0, 100, 200]
    assert len(json.loads(result.text)["entries"]) == 300


@pytest.mark.asyncio
async def test_para_de_paginar_quando_ultima_pagina_vem_incompleta():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", 0))
        calls.append(offset)
        if offset == 0:
            return works_response([{**JABA_WORK, "DOI": f"10.1/y{i}"} for i in range(100)])
        return works_response([JABA_WORK])

    source = make_source(handler)
    try:
        await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert calls == [0, 100]


@pytest.mark.asyncio
async def test_item_nao_article_e_ignorado():
    other = {**JABA_WORK, "type": "journal-issue", "DOI": "10.1/issue"}
    source = make_source(lambda _r: works_response([JABA_WORK, other]))
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    entries = json.loads(result.text)["entries"]
    assert [e["doi"] for e in entries] == ["10.1002/jaba.70077"]


@pytest.mark.asyncio
async def test_sem_issn_falha_sem_ir_a_rede():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deve haver requisição")

    source = make_source(handler)
    try:
        result = await source.fetch_works(None, last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "invalid_content"
    assert "ISSN" in (result.error or "")


# --- Classificação de erros -----------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [404, 410])
async def test_issn_inexistente_e_falha_permanente(status_code):
    source = make_source(lambda _r: httpx.Response(status_code))
    try:
        result = await source.fetch_works("0000-0000", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "invalid_content"


@pytest.mark.asyncio
async def test_429_e_transitorio_para_nao_punir_o_feed():
    source = make_source(lambda _r: httpx.Response(429))
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "transient_error"


@pytest.mark.asyncio
async def test_5xx_e_transitorio():
    source = make_source(lambda _r: httpx.Response(503))
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "transient_error"


@pytest.mark.asyncio
async def test_400_propaga_a_mensagem_do_crossref():
    """400 é erro nosso (parâmetro inválido), não bloqueio — precisa ser diagnosticável."""
    body = {
        "status": "failed",
        "message": [
            {
                "type": "select-not-available",
                "value": "language",
                "message": "Select 'language' specified but there is no such select",
            }
        ],
    }

    source = make_source(lambda _r: httpx.Response(400, json=body))
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "invalid_content"
    assert "select" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_corpo_nao_json_e_falha_permanente():
    source = make_source(lambda _r: httpx.Response(200, text="<html>challenge</html>"))
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "invalid_content"


@pytest.mark.asyncio
async def test_erro_de_rede_e_transitorio():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    source = make_source(handler)
    try:
        result = await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert result.status.value == "transient_error"


# --- Parâmetros enviados --------------------------------------------------


@pytest.mark.asyncio
async def test_works_envia_mailto_select_e_ordenacao():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return works_response([])

    source = make_source(handler)
    try:
        await source.fetch_works("1938-3703", last_successful_sync_at=None)
    finally:
        await source.close()

    assert seen["mailto"]
    assert seen["sort"] == "published"
    assert seen["order"] == "desc"
    assert "language" not in seen["select"]
    assert "DOI" in seen["select"]


@pytest.mark.asyncio
async def test_validate_issn_nao_envia_select():
    """A rota /journals/{issn} responde 400 se receber `select`."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(
            200, json={"message": {"title": "Journal of Applied Behavior Analysis"}}
        )

    source = make_source(handler)
    try:
        ok, title = await source.validate_issn("1938-3703")
    finally:
        await source.close()

    assert ok is True
    assert title == "Journal of Applied Behavior Analysis"
    assert "select" not in seen


@pytest.mark.asyncio
async def test_validate_issn_inexistente():
    source = make_source(lambda _r: httpx.Response(404))
    try:
        ok, message = await source.validate_issn("0000-0000")
    finally:
        await source.close()

    assert ok is False
    assert "não encontrado" in (message or "")
