"""Endpoints de consentimento + CSRF (header e fallback por campo de form)."""

import pytest
from httpx import AsyncClient


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
