"""
Gate de consentimento do analytics: config + consentimento + DNT + exclusões.

O middleware grava via get_session_context (engine própria), então os testes
espionam AnalyticsService com monkeypatch em vez de consultar o banco de teste.
"""

import json
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.config import settings
from app.core.cookie_consent import CONSENT_COOKIE_NAME
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def analytics_on(monkeypatch):
    monkeypatch.setattr(settings, "enable_analytics", True)


@pytest.fixture
def track_spy(monkeypatch):
    """Espião: registra chamadas de escrita do analytics sem tocar no banco."""
    calls: list[str] = []

    async def fake_track_event(*args, **kwargs):
        calls.append("track_event")

    async def fake_get_or_create_session(*args, **kwargs):
        calls.append("get_or_create_session")

    monkeypatch.setattr(AnalyticsService, "track_event", fake_track_event)
    monkeypatch.setattr(AnalyticsService, "get_or_create_session", fake_get_or_create_session)
    return calls


def _consent_cookie(analytics: bool = True) -> str:
    return json.dumps({
        "necessary": True,
        "analytics": analytics,
        "external_media": False,
        "marketing": False,
        "version": settings.cookie_consent_version,
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    })


@pytest.mark.asyncio
class TestSemConsentimento:
    async def test_nao_cria_cookie_nem_header_nem_evento(self, client: AsyncClient, analytics_on, track_spy):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "analytics_session_id" not in resp.cookies
        assert "X-Session-ID" not in resp.headers
        assert track_spy == []

    @pytest.mark.xfail(reason="banner chega na Task 7", strict=True)
    async def test_banner_e_apresentado(self, client: AsyncClient):
        resp = await client.get("/")
        assert 'id="cookie-banner"' in resp.text


@pytest.mark.asyncio
class TestConsentimentoRecusado:
    async def test_analytics_bloqueado(self, client: AsyncClient, analytics_on, track_spy):
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=False))
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "analytics_session_id" not in resp.cookies
        assert track_spy == []


@pytest.mark.asyncio
class TestConsentimentoAceito:
    async def test_coleta_funciona(self, client: AsyncClient, analytics_on, track_spy):
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=True))
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.cookies.get("analytics_session_id")
        assert resp.headers.get("X-Session-ID")
        assert "track_event" in track_spy

    async def test_config_desligada_vence_consentimento(self, client: AsyncClient, track_spy, monkeypatch):
        monkeypatch.setattr(settings, "enable_analytics", False)
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=True))
        resp = await client.get("/")
        assert "analytics_session_id" not in resp.cookies
        assert track_spy == []

    async def test_dnt_vence_consentimento(self, client: AsyncClient, analytics_on, track_spy):
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=True))
        resp = await client.get("/", headers={"DNT": "1"})
        assert "analytics_session_id" not in resp.cookies
        assert track_spy == []


@pytest.mark.asyncio
class TestRotasExcluidas:
    @pytest.mark.parametrize("path", [
        "/login", "/contact", "/health", "/static/css/output.css", "/privacy",
    ])
    async def test_rotas_excluidas_nao_rastreadas(self, client: AsyncClient, analytics_on, track_spy, path):
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=True))
        await client.get(path)
        assert track_spy == []

    async def test_exclusao_por_prefixo_segura(self, client: AsyncClient):
        """Unidade da função de exclusão (sem depender de rotas reais)."""
        from app.core.analytics_middleware import AnalyticsMiddleware

        mw = AnalyticsMiddleware.__new__(AnalyticsMiddleware)
        assert mw._is_excluded("/contact") is True
        assert mw._is_excluded("/contact/qualquer") is True
        assert mw._is_excluded("/contactos") is False
        assert mw._is_excluded("/admin/analytics") is True
        assert mw._is_excluded("/cookie-consent") is True
        assert mw._is_excluded("/articles") is False


@pytest.mark.asyncio
class TestRevogacao:
    async def test_pos_revogacao_middleware_nao_reseta_cookie(self, client: AsyncClient, analytics_on, track_spy):
        """Regressão: a resposta do revoke não pode ter o cookie re-setado pelo middleware,
        e requests seguintes sem consentimento não recriam o cookie."""
        # visita com consentimento → cookie criado
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=True))
        await client.get("/")
        # revoga via endpoint (rota excluída do tracking)
        # nota (a): o AsyncClient persiste cookies no seu próprio jar; o CSRFMiddleware
        # só reemite Set-Cookie quando a requisição chega sem o cookie, então o token
        # já setado por uma resposta anterior só aparece em client.cookies (jar), não
        # em resp.cookies (que reflete apenas o Set-Cookie daquela resposta específica).
        await client.get("/contact")
        token = client.cookies.get("csrf_token")
        resp = await client.post(
            "/cookie-consent",
            data={"action": "revoke", "csrf_token": token},
            follow_redirects=False,
        )
        set_cookies = resp.headers.get_list("set-cookie")
        analytics_headers = [c for c in set_cookies if c.startswith("analytics_session_id=")]
        # só o header de deleção; nenhum re-set com valor novo
        assert analytics_headers, "esperava header de deleção do analytics_session_id"
        assert all("Max-Age=0" in c or "expires" in c.lower() for c in analytics_headers)
        # request seguinte (sem cookie de consentimento) não recria nada
        client.cookies.delete(CONSENT_COOKIE_NAME)
        client.cookies.delete("analytics_session_id") if "analytics_session_id" in client.cookies else None
        resp2 = await client.get("/")
        assert "analytics_session_id" not in resp2.cookies


@pytest.mark.asyncio
class TestCookieAdulterado:
    async def test_cookie_invalido_bloqueia_e_nao_quebra(self, client: AsyncClient, analytics_on, track_spy):
        client.cookies.set(CONSENT_COOKIE_NAME, "lixo-nao-json")
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "analytics_session_id" not in resp.cookies
        assert track_spy == []

    async def test_versao_antiga_bloqueia(self, client: AsyncClient, analytics_on, track_spy):
        raw = _consent_cookie(analytics=True).replace(settings.cookie_consent_version, "0.1")
        client.cookies.set(CONSENT_COOKIE_NAME, raw)
        await client.get("/")
        assert track_spy == []


@pytest.mark.asyncio
class TestApiTrackingRespeitaConsentimento:
    async def test_track_sem_consentimento_nao_grava(self, client: AsyncClient, analytics_on, track_spy):
        resp = await client.post(
            "/api/v1/analytics/track",
            json={"event_type": "page_view", "event_name": "x"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert track_spy == []

    async def test_track_com_consentimento_grava(self, client: AsyncClient, analytics_on, track_spy):
        client.cookies.set(CONSENT_COOKIE_NAME, _consent_cookie(analytics=True))
        resp = await client.post(
            "/api/v1/analytics/track",
            json={"event_type": "page_view", "event_name": "x"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "track_event" in track_spy
