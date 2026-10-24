"""Testes da política de erros tipada do sync de feeds."""

from contextlib import asynccontextmanager
from datetime import datetime

import pytest

from app.models.feed import Feed, FeedJournalSource, SyncFrequency
from app.services.feed_aggregator import FeedAggregatorService
from app.services.feed_fetcher import FetchResult, FetchStatus


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, feed):
        self.feed = feed
        self.committed = False

    async def execute(self, *_args, **_kwargs):
        return FakeResult(self.feed)

    async def commit(self):
        self.committed = True

    async def flush(self):
        pass

    @asynccontextmanager
    async def begin_nested(self):
        yield None


def make_feed(error_count: int = 0) -> Feed:
    feed = Feed(name="teste", feed_url="https://example.com/feed")
    feed.id = 1
    feed.is_active = True
    feed.deactivated_by_errors = False
    feed.error_count = error_count
    feed.max_errors = 5
    feed.sync_frequency = SyncFrequency.HOURLY
    feed.total_articles = 0
    feed.custom_headers = None
    feed.http_etag = None
    feed.http_last_modified = None
    return feed


class StubFetcher:
    def __init__(self, result: FetchResult):
        self.result = result
        self.calls: list[dict] = []

    async def fetch(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.result

    async def close(self):
        pass


class StubCrossref:
    """Fake do CrossrefSource: registra a chamada e devolve um resultado fixo."""

    def __init__(self, result: FetchResult | None = None):
        self.result = result or FetchResult(
            status=FetchStatus.OK,
            text='{"entries": []}',
        )
        self.calls: list[dict] = []

    async def fetch_works(self, issn, **kwargs):
        self.calls.append({"issn": issn, **kwargs})
        return self.result

    async def validate_issn(self, issn):
        return True, "Periódico de teste"

    async def close(self):
        pass


def make_service(feed: Feed, fetch_result: FetchResult) -> FeedAggregatorService:
    return FeedAggregatorService(db=FakeDB(feed), fetcher=StubFetcher(fetch_result))


def make_crossref_service(feed: Feed, result: FetchResult | None = None) -> FeedAggregatorService:
    """Serviço roteado para o Crossref, com ambos os fakes injetados."""
    service = FeedAggregatorService(
        db=FakeDB(feed),
        fetcher=StubFetcher(FetchResult(status=FetchStatus.OK, text="<rss/>")),
        crossref=StubCrossref(result),
    )
    return service


@pytest.mark.asyncio
async def test_erro_transitorio_nao_incrementa_error_count():
    feed = make_feed(error_count=2)
    service = make_service(feed, FetchResult(status=FetchStatus.TRANSIENT_ERROR, error="HTTP 502"))
    result = await service.sync_feed(feed_id=1)
    assert result.success is False
    assert feed.error_count == 2
    assert feed.last_error == "HTTP 502"


@pytest.mark.asyncio
async def test_bloqueio_incrementa_error_count():
    feed = make_feed(error_count=0)
    service = make_service(
        feed, FetchResult(status=FetchStatus.BLOCKED, error="HTTP 403 (impersonado)")
    )
    result = await service.sync_feed(feed_id=1)
    assert result.success is False
    assert feed.error_count == 1


@pytest.mark.asyncio
async def test_not_modified_conta_como_sucesso_e_zera_erros():
    feed = make_feed(error_count=3)
    service = make_service(feed, FetchResult(status=FetchStatus.NOT_MODIFIED))
    result = await service.sync_feed(feed_id=1)
    assert result.success is True
    assert result.new_articles == 0
    assert feed.error_count == 0
    assert feed.last_error is None


@pytest.mark.asyncio
async def test_gone_tenta_redescoberta_antes_de_falhar(monkeypatch):
    feed = make_feed(error_count=0)
    service = make_service(feed, FetchResult(status=FetchStatus.GONE, error="HTTP 410"))

    rediscover_calls: list[int] = []

    async def fake_rediscover(f):
        rediscover_calls.append(f.id)
        return None

    monkeypatch.setattr(service, "_try_rediscover", fake_rediscover)
    result = await service.sync_feed(feed_id=1)
    assert rediscover_calls == [1]
    assert result.success is False
    assert feed.error_count == 1


@pytest.mark.asyncio
async def test_sync_ok_persiste_etag_e_last_modified():
    feed = make_feed()
    rss = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>"""
    service = make_service(
        feed,
        FetchResult(
            status=FetchStatus.OK,
            text=rss,
            etag='"novo-etag"',
            last_modified="Thu, 02 Jan 2026 00:00:00 GMT",
        ),
    )
    result = await service.sync_feed(feed_id=1)
    assert result.success is True
    assert feed.http_etag == '"novo-etag"'
    assert feed.http_last_modified == "Thu, 02 Jan 2026 00:00:00 GMT"


@pytest.mark.asyncio
async def test_fetch_recebe_etag_e_custom_headers_do_feed():
    feed = make_feed()
    feed.http_etag = '"etag-salvo"'
    feed.custom_headers = '{"X-Api-Key": "s3cr3t"}'
    service = make_service(feed, FetchResult(status=FetchStatus.NOT_MODIFIED))
    await service.sync_feed(feed_id=1)
    call = service.fetcher.calls[0]
    assert call["etag"] == '"etag-salvo"'
    assert call["custom_headers"] == {"X-Api-Key": "s3cr3t"}


# --- Resposta HTTP 200 cujo corpo NÃO é RSS/Atom ---------------------------
# A Springer passou a devolver o challenge anti-bot da Fastly com HTTP 200 e
# corpo HTML. Sem validação de conteúdo o sync marcava sucesso, zerava
# error_count e avançava last_successful_sync_at — escondendo ~7 semanas sem
# ingestão de periódicos.

CHALLENGE_HTML = """<!DOCTYPE html>
<html lang="en">
  <head><title>Client Challenge</title></head>
  <body><p>Please enable JavaScript to proceed.</p></body>
</html>"""

RSS_COM_ITEM = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
  <item><title>Artigo</title><link>https://example.com/a</link></item>
</channel></rss>"""

RSS_VAZIO = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>"""

ATOM_VAZIO = (
    """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title></feed>"""
)

SYNC_ANTERIOR = datetime(2026, 8, 4, 12, 0, 0)


def make_feed_com_sucesso_anterior(error_count: int = 0) -> Feed:
    feed = make_feed(error_count=error_count)
    feed.last_successful_sync_at = SYNC_ANTERIOR
    return feed


@pytest.mark.asyncio
async def test_html_com_http_200_nao_conta_como_sucesso():
    feed = make_feed_com_sucesso_anterior(error_count=0)
    service = make_service(
        feed,
        FetchResult(
            status=FetchStatus.OK,
            text=CHALLENGE_HTML,
            etag='"challenge"',
        ),
    )

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert result.new_articles == 0
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"


@pytest.mark.asyncio
async def test_html_com_http_200_incrementa_error_count():
    feed = make_feed_com_sucesso_anterior(error_count=2)
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=CHALLENGE_HTML))

    await service.sync_feed(feed_id=1)

    assert feed.error_count == 3


@pytest.mark.asyncio
async def test_html_com_http_200_preserva_last_successful_sync_at():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=CHALLENGE_HTML))

    await service.sync_feed(feed_id=1)

    assert feed.last_successful_sync_at == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_html_sem_doctype_nem_content_type_tambem_falha():
    """A detecção não pode depender do header: corpo HTML cru também é inválido."""
    feed = make_feed_com_sucesso_anterior()
    service = make_service(
        feed,
        FetchResult(status=FetchStatus.OK, text="<html><body>bloqueado</body></html>"),
    )

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"
    assert feed.last_successful_sync_at == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_corpo_vazio_nao_conta_como_sucesso():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=""))

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"
    assert feed.last_successful_sync_at == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_corpo_json_nao_conta_como_sucesso():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text='{"items": []}'))

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.last_error == "Invalid feed response: conteúdo não é RSS/Atom"


@pytest.mark.asyncio
async def test_rss_valido_vazio_continua_sendo_sucesso():
    """Feed estruturalmente válido com 0 itens NÃO é falha (§9 do hotfix)."""
    feed = make_feed_com_sucesso_anterior(error_count=3)
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=RSS_VAZIO))

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert result.new_articles == 0
    assert feed.error_count == 0
    assert feed.last_successful_sync_at != SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_atom_valido_vazio_continua_sendo_sucesso():
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=ATOM_VAZIO))

    result = await service.sync_feed(feed_id=1)

    assert result.success is True


@pytest.mark.asyncio
async def test_rss_valido_com_item_continua_sendo_processado(monkeypatch):
    """Feed saudável não pode regredir: as entradas seguem sendo processadas."""
    feed = make_feed_com_sucesso_anterior()
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=RSS_COM_ITEM))

    async def fake_process(_feed, _entry):
        return 42, {"is_open_access": False}

    monkeypatch.setattr(service, "_process_feed_entry", fake_process)

    dispatched: list[int] = []

    async def fake_dispatch(article_id):
        dispatched.append(article_id)
        return "job-1"

    monkeypatch.setattr("app.services.feed_aggregator.dispatch_classify_article", fake_dispatch)

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert result.new_articles == 1
    assert dispatched == [42]


# --- Roteamento para o Crossref (ADR-0007) ---------------------------------
# Um feed marcado como CROSSREF não pode tocar no RSS da editora: é ele que
# responde 403/anti-bot. O roteamento é o que decide se a ingestão funciona.


def make_crossref_feed(issn: str = "1938-3703", **kwargs) -> Feed:
    feed = make_feed(**kwargs)
    feed.journal_source = FeedJournalSource.CROSSREF
    feed.issn = issn
    feed.journal_name = "Journal of Applied Behavior Analysis"
    return feed


@pytest.mark.asyncio
async def test_feed_crossref_usa_crossref_e_nao_o_rss_da_editora():
    feed = make_crossref_feed()
    service = make_crossref_service(feed)

    await service.sync_feed(feed_id=1)

    assert service.crossref.calls[0]["issn"] == "1938-3703"
    # O fetcher de RSS não pode ter sido chamado: bater nele é o que falha.
    assert service.fetcher.calls == []


@pytest.mark.asyncio
async def test_feed_crossref_recebe_last_successful_sync_at_para_a_janela():
    feed = make_crossref_feed()
    feed.last_successful_sync_at = SYNC_ANTERIOR
    service = make_crossref_service(feed)

    await service.sync_feed(feed_id=1)

    assert service.crossref.calls[0]["last_successful_sync_at"] == SYNC_ANTERIOR


@pytest.mark.asyncio
async def test_feed_crossref_nao_faz_redescoberta_de_url():
    """A URL do Crossref é derivada do ISSN; não há o que redescobrir."""
    feed = make_crossref_feed()
    service = make_crossref_service(feed)

    rediscover_calls: list[int] = []

    async def fake_rediscover(f):
        rediscover_calls.append(f.id)
        return "https://example.com/outro"

    monkeypatch_calls = fake_rediscover
    service._try_rediscover = monkeypatch_calls  # type: ignore[assignment]

    await service.sync_feed(feed_id=1)

    assert rediscover_calls == []


@pytest.mark.asyncio
async def test_crossref_ok_processa_entradas_como_artigos(monkeypatch):
    """As entradas do Crossref passam pelo mesmo pipeline de ingestão."""
    import json as _json

    feed = make_crossref_feed()
    payload = _json.dumps(
        {"entries": [{"id": "doi:10.1/x", "link": "https://doi.org/10.1/x", "title": "T"}]}
    )
    service = make_crossref_service(feed, FetchResult(status=FetchStatus.OK, text=payload))

    seen: list[dict] = []

    async def fake_process(_feed, entry):
        seen.append(entry)
        return 7, {"is_open_access": False}

    monkeypatch.setattr(service, "_process_feed_entry", fake_process)

    async def fake_dispatch(_article_id):
        return "job"

    monkeypatch.setattr("app.services.feed_aggregator.dispatch_classify_article", fake_dispatch)

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert result.new_articles == 1
    assert seen[0]["id"] == "doi:10.1/x"


@pytest.mark.asyncio
async def test_crossref_com_falha_nao_marca_sucesso():
    feed = make_crossref_feed()
    service = make_crossref_service(
        feed,
        FetchResult(status=FetchStatus.INVALID_CONTENT, error="HTTP 404: ISSN não encontrado"),
    )

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.error_count == 1
    assert "404" in (feed.last_error or "")


@pytest.mark.asyncio
async def test_crossref_sem_issn_falha_sem_tocar_o_rss():
    feed = make_crossref_feed()
    feed.issn = None
    service = make_crossref_service(
        feed,
        FetchResult(
            status=FetchStatus.INVALID_CONTENT,
            error="Feed sem ISSN configurado para ingestão via Crossref",
        ),
    )

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert service.fetcher.calls == []


@pytest.mark.asyncio
async def test_crossref_nao_tenta_scraping_de_autores(monkeypatch):
    """O original_url aponta para a editora bloqueada; não pode ser buscado."""
    import json as _json

    feed = make_crossref_feed()
    payload = _json.dumps(
        {"entries": [{"id": "doi:10.1/x", "link": "https://doi.org/10.1/x", "title": "T"}]}
    )
    service = make_crossref_service(feed, FetchResult(status=FetchStatus.OK, text=payload))

    scraped_urls: list[str] = []

    class RecordingClient:
        async def get(self, url, **_kwargs):
            scraped_urls.append(url)

            class Response:
                status_code = 200
                text = "<html></html>"

            return Response()

    service.http_client = RecordingClient()  # type: ignore[assignment]

    await service.sync_feed(feed_id=1)

    assert scraped_urls == []


# --- Desativação por max_errors (defeito D2) -------------------------------


@pytest.mark.asyncio
async def test_erro_ao_atingir_max_errors_desativa_o_feed():
    """D2: `max_errors` precisa surtir efeito, não só existir na coluna."""
    feed = make_feed(error_count=4)  # max_errors=5 -> a próxima falha desativa
    service = make_service(feed, FetchResult(status=FetchStatus.BLOCKED, error="HTTP 403"))

    result = await service.sync_feed(feed_id=1)

    assert result.success is False
    assert feed.error_count == 5
    assert feed.is_active is False


@pytest.mark.asyncio
async def test_feed_nao_e_desativado_antes_do_limite():
    feed = make_feed(error_count=1)
    service = make_service(feed, FetchResult(status=FetchStatus.BLOCKED, error="HTTP 403"))

    await service.sync_feed(feed_id=1)

    assert feed.error_count == 2
    assert feed.is_active is True


@pytest.mark.asyncio
async def test_erro_transitorio_nao_desativa_mesmo_no_limite():
    """429/5xx não podem desativar: não são defeito da fonte."""
    feed = make_feed(error_count=9)
    service = make_service(feed, FetchResult(status=FetchStatus.TRANSIENT_ERROR, error="HTTP 502"))

    await service.sync_feed(feed_id=1)

    assert feed.error_count == 9
    assert feed.is_active is True


@pytest.mark.asyncio
async def test_falha_de_conteudo_invalido_tambem_desativa():
    """O challenge da Springer é permanente; deve entrar no limite."""
    feed = make_feed(error_count=4)
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=CHALLENGE_HTML))

    await service.sync_feed(feed_id=1)

    assert feed.is_active is False


@pytest.mark.asyncio
async def test_desativacao_marca_a_origem_como_erro():
    """O marcador é o que habilita a reativação automática e protege a curadoria."""
    feed = make_feed(error_count=4)
    service = make_service(feed, FetchResult(status=FetchStatus.BLOCKED, error="HTTP 403"))

    await service.sync_feed(feed_id=1)

    assert feed.is_active is False
    assert feed.deactivated_by_errors is True


@pytest.mark.asyncio
async def test_sonda_bem_sucedida_reativa_o_feed():
    """Sem isto, a sonda de recuperação não recuperaria nada."""
    feed = make_feed(error_count=5)
    feed.is_active = False
    feed.deactivated_by_errors = True
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=RSS_VAZIO))

    result = await service.sync_feed(feed_id=1)

    assert result.success is True
    assert feed.is_active is True
    assert feed.deactivated_by_errors is False
    assert feed.error_count == 0


@pytest.mark.asyncio
async def test_sonda_nao_reativa_feed_desativado_pela_curadoria():
    """Desativação manual é definitiva: nenhum código a desfaz."""
    feed = make_feed(error_count=5)
    feed.is_active = False
    feed.deactivated_by_errors = False
    service = make_service(feed, FetchResult(status=FetchStatus.OK, text=RSS_VAZIO))

    await service.sync_feed(feed_id=1)

    assert feed.is_active is False
