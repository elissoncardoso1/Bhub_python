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
