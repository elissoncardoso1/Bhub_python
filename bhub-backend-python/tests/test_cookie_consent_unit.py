"""Testes do módulo de consentimento de cookies e configurações de privacidade."""

import json

from fastapi import FastAPI, Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.config import Settings
from app.core import cookie_consent as cc


def test_analytics_desativado_por_padrao(monkeypatch):
    """enable_analytics deve ser False por padrão (privacidade por design)."""
    monkeypatch.delenv("ENABLE_ANALYTICS", raising=False)
    s = Settings(_env_file=None)
    assert s.enable_analytics is False


def test_settings_de_consentimento_existem():
    s = Settings(_env_file=None)
    assert s.cookie_consent_enabled is True
    assert s.cookie_consent_version == "1.0"
    assert s.analytics_respect_dnt is True


def _cookie(payload: dict) -> str:
    return json.dumps(payload)


def _valid_payload(**overrides) -> dict:
    base = {
        "necessary": True,
        "analytics": True,
        "external_media": False,
        "marketing": False,
        "version": "1.0",
        "updated_at": "2026-07-16T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestParseConsentCookie:
    def test_cookie_ausente_retorna_estado_nao_decidido(self):
        state = cc.parse_consent_cookie(None)
        assert state.decided is False
        assert state.analytics is False
        assert state.necessary is True  # sempre

    def test_cookie_valido(self):
        state = cc.parse_consent_cookie(_cookie(_valid_payload()))
        assert state.decided is True
        assert state.analytics is True
        assert state.external_media is False
        assert state.marketing is False

    def test_json_invalido_nao_quebra(self):
        assert cc.parse_consent_cookie("{{{nao-e-json").decided is False

    def test_json_nao_dict_rejeitado(self):
        assert cc.parse_consent_cookie('["a"]').decided is False

    def test_tipos_errados_rejeitados(self):
        raw = _cookie(_valid_payload(analytics="sim"))
        assert cc.parse_consent_cookie(raw).decided is False

    def test_cookie_gigante_rejeitado(self):
        raw = _cookie(_valid_payload()) + " " * 2048
        assert cc.parse_consent_cookie(raw).decided is False

    def test_versao_antiga_nao_e_decisao_atual(self):
        raw = _cookie(_valid_payload(version="0.9"))
        state = cc.parse_consent_cookie(raw)
        assert state.decided is False
        assert state.analytics is False  # escolha antiga não autoriza nada

    def test_necessary_false_e_ignorado(self):
        """Cliente não pode desativar a categoria necessary."""
        raw = _cookie(_valid_payload(necessary=False))
        state = cc.parse_consent_cookie(raw)
        assert state.necessary is True


class TestIsGranted:
    def _build_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/set")
        def set_cookie() -> Response:
            resp = Response()
            cc.set_consent_cookie(
                resp, {"analytics": True, "external_media": True, "marketing": True}
            )
            return resp

        @app.get("/check/{category}")
        def check(category: str, request: Request) -> dict:
            return {"granted": cc.is_granted(request, category)}

        return app

    def test_categoria_desconhecida_retorna_false_mesmo_com_cookie_valido(self):
        """`is_granted` só reconhece necessary/analytics/external_media/marketing."""
        client = TestClient(self._build_app())
        client.get("/set")

        assert client.get("/check/decided").json()["granted"] is False
        assert client.get("/check/inexistente").json()["granted"] is False
        # sanidade: categoria válida continua concedida
        assert client.get("/check/analytics").json()["granted"] is True


class TestSerializeAndCookie:
    def test_serialize_roundtrip(self):
        raw = cc.serialize_consent({"analytics": True, "external_media": False, "marketing": False})
        state = cc.parse_consent_cookie(raw)
        assert state.decided is True and state.analytics is True

    def test_serialize_nao_vaza_dados_pessoais(self):
        raw = cc.serialize_consent({"analytics": True, "external_media": False, "marketing": False})
        data = json.loads(raw)
        assert set(data.keys()) == {
            "necessary", "analytics", "external_media", "marketing", "version", "updated_at",
        }

    def test_set_consent_cookie_flags(self):
        resp = Response()
        cc.set_consent_cookie(resp, {"analytics": False, "external_media": False, "marketing": False})
        header = resp.headers["set-cookie"]
        assert "bhub_consent=" in header
        assert "SameSite=lax" in header or "samesite=lax" in header.lower()
        assert f"Max-Age={cc.CONSENT_COOKIE_MAX_AGE}" in header


class TestCookieRoundTripHttp:
    """Regressão: o valor JSON passa pelo quoting do `http.cookies` no Set-Cookie
    (DQUOTE + escapes tipo \\054 para a vírgula) e precisa voltar intacto quando
    o client reenvia o cookie e `request.cookies` faz o unquote."""

    def _build_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/set")
        def set_cookie() -> Response:
            resp = Response()
            cc.set_consent_cookie(
                resp, {"analytics": True, "external_media": False, "marketing": False}
            )
            return resp

        @app.get("/read")
        def read_cookie(request: Request) -> dict:
            return cc.get_consent(request).as_dict()

        return app

    def test_set_e_ler_cookie_via_http_completo(self):
        client = TestClient(self._build_app())

        set_resp = client.get("/set")
        assert set_resp.status_code == 200
        assert cc.CONSENT_COOKIE_NAME in client.cookies

        read_resp = client.get("/read")
        assert read_resp.status_code == 200
        data = read_resp.json()
        assert data["decided"] is True
        assert data["analytics"] is True
        assert data["external_media"] is False
        assert data["marketing"] is False
