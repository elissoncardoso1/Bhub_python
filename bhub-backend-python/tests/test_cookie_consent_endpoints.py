"""Endpoints de consentimento + CSRF (header e fallback por campo de form)."""

import json
from http.cookies import SimpleCookie

import pytest
from httpx import AsyncClient

from app.core.cookie_consent import CONSENT_COOKIE_NAME
from app.web.consent import _safe_next


@pytest.mark.parametrize(
    ("next_path", "expected"),
    [
        ("/articles", "/articles"),
        (None, "/"),
        ("", "/"),
        ("https://evil.example", "/"),
        ("//evil.com", "/"),
        ("/\\evil.com", "/"),
        ("/x\rSet-Cookie:y", "/"),
        ("/x\x00", "/"),
    ],
)
def test_safe_next(next_path: str | None, expected: str) -> None:
    assert _safe_next(next_path) == expected


async def _get_csrf(client: AsyncClient) -> str:
    """GET em página SSR para o CSRFMiddleware setar o cookie csrf_token."""
    resp = await client.get("/contact")
    assert resp.status_code == 200
    token = resp.cookies.get("csrf_token")
    assert token
    return token


@pytest.mark.asyncio
async def test_contact_post_com_csrf_no_campo_form_passa(client: AsyncClient):
    """Regressão do fallback usando a rota web /contact já existente."""
    token = await _get_csrf(client)
    resp = await client.post(
        "/contact",
        data={
            "csrf_token": token,
            "name": "Fulano Teste",
            "email": "fulano@example.com",
            "subject": "Assunto de teste",
            "message": "Mensagem com mais de dez caracteres.",
        },
    )
    assert resp.status_code == 200
    assert "sucesso" in resp.text.lower()


@pytest.mark.asyncio
async def test_post_form_sem_nenhum_token_e_rejeitado(client: AsyncClient):
    """Cookie existe, mas nem header nem campo → 403."""
    await _get_csrf(client)
    resp = await client.post(
        "/contact",
        data={
            "name": "Fulano Teste",
            "email": "fulano@example.com",
            "subject": "Assunto de teste",
            "message": "Mensagem com mais de dez caracteres.",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_form_com_token_forjado_e_rejeitado(client: AsyncClient):
    await _get_csrf(client)
    resp = await client.post(
        "/contact",
        data={
            "csrf_token": "token-forjado",
            "name": "Fulano Teste",
            "email": "fulano@example.com",
            "subject": "Assunto de teste",
            "message": "Mensagem com mais de dez caracteres.",
        },
    )
    assert resp.status_code == 403


def _consent_from_setcookie(resp) -> dict:
    raw = resp.cookies.get(CONSENT_COOKIE_NAME)
    assert raw, "cookie bhub_consent não foi setado"
    # httpx devolve o valor ainda com o quoting do http.cookies (aspas + escapes
    # octais, pois o JSON contém vírgulas/dois-pontos); reprocessa via SimpleCookie
    # para obter o valor "desquotado" antes do json.loads.
    jar = SimpleCookie()
    jar.load(f"{CONSENT_COOKIE_NAME}={raw}")
    return json.loads(jar[CONSENT_COOKIE_NAME].value)


@pytest.mark.asyncio
class TestConsentEndpoints:
    async def test_accept_all(self, client: AsyncClient):
        token = await _get_csrf(client)
        resp = await client.post(
            "/cookie-consent",
            data={"action": "accept_all", "csrf_token": token, "next": "/articles"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/articles"
        data = _consent_from_setcookie(resp)
        assert data["analytics"] is True and data["marketing"] is True

    async def test_reject_all(self, client: AsyncClient):
        token = await _get_csrf(client)
        resp = await client.post(
            "/cookie-consent",
            data={"action": "reject_all", "csrf_token": token},
            follow_redirects=False,
        )
        data = _consent_from_setcookie(resp)
        assert data["analytics"] is False
        assert data["necessary"] is True

    async def test_save_personalizado(self, client: AsyncClient):
        token = await _get_csrf(client)
        resp = await client.post(
            "/cookie-consent",
            data={"action": "save", "csrf_token": token, "analytics": "on"},
            follow_redirects=False,
        )
        data = _consent_from_setcookie(resp)
        assert data["analytics"] is True
        assert data["external_media"] is False

    async def test_cliente_nao_desativa_necessary(self, client: AsyncClient):
        """Mesmo enviando necessary=off, ela permanece True."""
        token = await _get_csrf(client)
        resp = await client.post(
            "/cookie-consent",
            data={"action": "save", "csrf_token": token, "necessary": "off"},
            follow_redirects=False,
        )
        assert _consent_from_setcookie(resp)["necessary"] is True

    async def test_revoke_limpa_cookies(self, client: AsyncClient):
        token = await _get_csrf(client)
        await client.post(
            "/cookie-consent",
            data={"action": "accept_all", "csrf_token": token},
            follow_redirects=False,
        )
        resp = await client.post(
            "/cookie-consent",
            data={"action": "revoke", "csrf_token": token},
            follow_redirects=False,
        )
        set_cookies = resp.headers.get_list("set-cookie")
        assert any(CONSENT_COOKIE_NAME in c and ("Max-Age=0" in c or "expires" in c.lower()) for c in set_cookies)
        # analytics_session_id também precisa ser uma deleção de fato (Max-Age=0
        # ou expiração no passado), não só um Set-Cookie qualquer com esse nome.
        assert any(
            "analytics_session_id" in c and ("Max-Age=0" in c or "expires" in c.lower())
            for c in set_cookies
        )

    async def test_action_invalida_retorna_400(self, client: AsyncClient):
        token = await _get_csrf(client)
        resp = await client.post(
            "/cookie-consent",
            data={"action": "hackear", "csrf_token": token},
        )
        assert resp.status_code == 400

    async def test_next_externo_e_neutralizado(self, client: AsyncClient):
        """Anti open-redirect: next só pode ser caminho relativo interno."""
        token = await _get_csrf(client)
        resp = await client.post(
            "/cookie-consent",
            data={"action": "reject_all", "csrf_token": token, "next": "https://evil.example"},
            follow_redirects=False,
        )
        assert resp.headers["location"] == "/"

    async def test_get_api_estado_atual(self, client: AsyncClient):
        resp = await client.get("/api/v1/cookie-consent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["decided"] is False and body["necessary"] is True
