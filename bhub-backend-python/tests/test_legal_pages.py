"""Banner de consentimento, central de preferências, footer e páginas legais."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestBannerConsentimento:
    async def test_primeira_visita_mostra_banner_acessivel(self, client: AsyncClient):
        resp = await client.get("/")
        html = resp.text
        assert 'id="cookie-banner"' in html
        assert "Sua privacidade no BHUB" in html
        assert "Aceitar opcionais" in html
        assert "Recusar opcionais" in html
        assert "Configurar" in html
        assert 'role="region"' in html

    async def test_banner_nao_reaparece_apos_escolha(self, client: AsyncClient):
        resp = await client.get("/contact")
        token = client.cookies.get("csrf_token")
        await client.post(
            "/cookie-consent",
            data={"action": "reject_all", "csrf_token": token},
            follow_redirects=False,
        )
        resp = await client.get("/")
        assert 'id="cookie-banner"' not in resp.text
        # central continua acessível (dialog presente para reabertura)
        assert 'id="cookie-preferences"' in resp.text

    async def test_central_tem_necessary_travada(self, client: AsyncClient):
        resp = await client.get("/")
        html = resp.text
        assert 'name="analytics"' in html
        assert "disabled" in html  # checkbox necessary
        assert "Salvar preferências" in html

    async def test_next_preserva_query_string(self, client: AsyncClient):
        await client.get("/contact")
        token = client.cookies.get("csrf_token")
        resp = await client.post(
            "/cookie-consent",
            data={
                "action": "accept_all",
                "csrf_token": token,
                "next": "/articles?category=aba&page=3",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/articles?category=aba&page=3"


@pytest.mark.asyncio
class TestFooter:
    async def test_footer_tem_os_quatro_links(self, client: AsyncClient):
        html = (await client.get("/")).text
        assert 'href="/privacy"' in html
        assert 'href="/cookies"' in html
        assert 'href="/terms"' in html
        assert "Preferências de cookies" in html
        assert "data-consent-open" in html

    async def test_gatilho_de_preferencias_persiste_apos_escolha(self, client: AsyncClient):
        """Crítico do review da Task 7: a central deve ser reabrível após decidir."""
        await client.get("/contact")
        token = client.cookies.get("csrf_token")
        await client.post(
            "/cookie-consent",
            data={"action": "reject_all", "csrf_token": token},
            follow_redirects=False,
        )
        html = (await client.get("/")).text
        assert 'id="cookie-banner"' not in html          # banner some
        assert 'id="cookie-preferences"' in html          # dialog presente
        assert "data-consent-open" in html                # gatilho persistente (footer)


@pytest.mark.asyncio
class TestPaginasLegais:
    @pytest.mark.parametrize("path,titulo", [
        ("/privacy", "Política de Privacidade"),
        ("/cookies", "Política de Cookies"),
        ("/terms", "Termos de Uso"),
    ])
    async def test_pagina_responde_200(self, client: AsyncClient, path, titulo):
        resp = await client.get(path)
        assert resp.status_code == 200
        assert titulo in resp.text

    async def test_privacy_tem_placeholders_e_secoes_lgpd(self, client: AsyncClient):
        html = (await client.get("/privacy")).text
        assert "A CONFIRMAR" in html          # placeholders explícitos, nada inventado
        assert "ANPD" in html
        assert "Direitos" in html

    async def test_cookies_lista_cookies_reais(self, client: AsyncClient):
        html = (await client.get("/cookies")).text
        for nome in ("access_token", "csrf_token", "analytics_session_id", "bhub_consent"):
            assert nome in html
        # cookie de refresh — nome real confirmado em app/core/refresh_token.py:26
        assert "refresh_token" in html

    async def test_paginas_legais_acessiveis_com_opcionais_recusados(self, client: AsyncClient):
        await client.get("/contact")
        token = client.cookies.get("csrf_token")
        await client.post("/cookie-consent", data={"action": "reject_all", "csrf_token": token}, follow_redirects=False)
        for path in ("/privacy", "/cookies", "/terms", "/contact"):
            assert (await client.get(path)).status_code == 200
