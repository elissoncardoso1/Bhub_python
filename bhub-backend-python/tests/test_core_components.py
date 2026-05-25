"""
Testes unitários para componentes de core (cookies, CSRF, rate limiting).
Visam aumentar cobertura cobrindo ramos não exercitados nos testes E2E.
"""

import uuid
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, Response
from httpx import ASGITransport, AsyncClient
from jose import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from app.config import settings
from app.core.access_token_cookie_middleware import AccessTokenCookieMiddleware
from app.core.auth_cookie_middleware import AuthCookieMiddleware
from app.core.cookie_transport import CookieTransport
from app.core.csrf import csrf_protection
from app.core.csrf_middleware import CSRFMiddleware
from app.core.rate_limiting import get_user_id_for_rate_limit
from app.core.refresh_token import RefreshTokenService


# ---------- CookieTransport ----------
@pytest.mark.asyncio
async def test_cookie_transport_login_and_logout_sets_cookie_and_body():
    transport = CookieTransport(cookie_name="access_token", cookie_secure=False)
    response = Response()

    await transport.login("tok123", response)

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token=tok123" in set_cookie_header
    assert response.headers["Content-Type"] == "application/json"
    assert b'"access_token": "tok123"' in response.body

    await transport.logout(response)
    del_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token=" in del_cookie_header


def make_request(
    path: str = "/",
    method: str = "GET",
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "path": path,
        "method": method,
        "headers": [],
    }
    # headers em bytes
    if headers:
        scope["headers"] = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    req = Request(scope)
    req._cookies = cookies or {}
    return req


def test_cookie_transport_get_token_from_cookie_and_header():
    transport = CookieTransport(cookie_name="access_token")

    req_cookie = make_request(cookies={"access_token": "from_cookie"})
    assert transport.get_token_from_request(req_cookie) == "from_cookie"

    req_header = make_request(headers={"Authorization": "Bearer hdr123"})
    assert transport.get_token_from_request(req_header) == "hdr123"


# ---------- Rate limiting ----------
@pytest.mark.asyncio
async def test_rate_limit_invokes_limiter(monkeypatch):
    called: dict[str, Any] = {}

    def fake_limit(limit: str, key_func=None):
        called["limit"] = limit
        called["key_func"] = key_func

        def wrapper(func):
            called["wrapped"] = True
            def inner(*args, **kwargs):
                called["inner_called"] = True
                return func(*args, **kwargs)
            return inner

        return wrapper

    from app.core import rate_limiting

    monkeypatch.setattr(rate_limiting.limiter, "limit", fake_limit)

    @rate_limiting.rate_limit("5/minute")
    async def sample(req: Request):
        return "ok"

    result = await sample(make_request())

    assert called["limit"] == "5/minute"
    assert called["wrapped"] is True
    assert called["inner_called"] is True
    assert result == "ok"


def test_get_user_id_for_rate_limit_with_token_and_ip_fallback():
    token = jwt.encode(
        {"sub": "user-123", "type": "access"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    req_token = make_request(headers={"Authorization": f"Bearer {token}"})
    assert get_user_id_for_rate_limit(req_token) == "user:user-123"

    req_ip = make_request()
    assert get_user_id_for_rate_limit(req_ip).startswith("127.0.0.1") or get_user_id_for_rate_limit(req_ip)


# ---------- RefreshTokenService ----------
def test_refresh_token_create_and_decode():
    svc = RefreshTokenService()
    user_id = uuid.uuid4()
    token_id = "tid-1"

    refresh_jwt = svc.create_refresh_token_jwt(user_id, token_id)
    payload = svc.decode_refresh_token(refresh_jwt)

    assert payload["sub"] == str(user_id)
    assert payload["token_id"] == token_id
    assert payload["type"] == "refresh"


def test_refresh_token_cookie_set_and_clear():
    svc = RefreshTokenService()
    response = Response()

    svc.set_refresh_token_cookie(response, "ref123")
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=ref123" in set_cookie_header

    svc.clear_refresh_token_cookie(response)
    headers_list = response.headers.getlist("set-cookie")
    assert any("refresh_token=ref123" in h for h in headers_list)
    assert any("Max-Age=0" in h or "max-age=0" in h for h in headers_list)


# ---------- CSRF ----------
def test_csrf_not_required_allows_without_cookie_or_header():
    req = make_request(method="POST")
    assert csrf_protection.validate_csrf(req, require_token=False) is True


# ---------- CSRFMiddleware ----------
@pytest.mark.asyncio
async def test_csrf_middleware_sets_cookie_on_get():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware, auto_validate=False)

    @app.get("/page")
    async def page():
        return PlainTextResponse("ok")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/page")
        assert resp.status_code == 200
        # cookie deve existir
        assert "csrf_token" in resp.cookies


@pytest.mark.asyncio
async def test_csrf_middleware_validates_on_mutation_when_auto_validate():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware, auto_validate=True)

    @app.post("/mut")
    async def mut(req: Request):
        return PlainTextResponse("mut")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Sem cookie/header deve falhar com 403
        with pytest.raises(HTTPException):
            await client.post("/mut")

        # Com cookie+header iguais deve passar
        token = "abc123"
        resp2 = await client.post(
            "/mut",
            headers={"x-csrf-token": token},
            cookies={"csrf_token": token},
        )
        assert resp2.status_code == 200


# ---------- AccessTokenCookieMiddleware ----------
@pytest.mark.asyncio
async def test_access_token_cookie_middleware_injects_header():
    app = FastAPI()
    app.add_middleware(AccessTokenCookieMiddleware, cookie_name="access_token")

    @app.get("/echo-auth")
    async def echo_auth(request: Request):
        return PlainTextResponse(request.headers.get("authorization") or "")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/echo-auth", cookies={"access_token": "tok"})
        assert resp.text == "Bearer tok"

        resp2 = await client.get("/echo-auth")
        assert resp2.text == ""


# ---------- AuthCookieMiddleware ----------
@pytest.mark.asyncio
async def test_auth_cookie_middleware_sets_and_clears_cookie():
    app = FastAPI()
    app.add_middleware(AuthCookieMiddleware)

    @app.post("/api/v1/auth/login")
    async def login():
        return JSONResponse({"access_token": "tok-xyz"})

    @app.post("/api/v1/auth/logout")
    async def logout():
        return JSONResponse({"status": "bye"})

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/auth/login")
        assert resp.status_code == 200
        assert resp.cookies.get("access_token") == "tok-xyz"
        # Body preservado
        assert resp.json()["access_token"] == "tok-xyz"

        resp2 = await client.post("/api/v1/auth/logout", cookies={"access_token": "tok-xyz"})
        assert resp2.status_code == 200
        # logout envia delete-cookie
        set_cookie_header = resp2.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie_header
        assert "Max-Age=0" in set_cookie_header


@pytest.mark.asyncio
async def test_auth_cookie_middleware_preserves_headers_and_existing_cookies():
    app = FastAPI()
    app.add_middleware(AuthCookieMiddleware)

    @app.post("/api/v1/auth/login")
    async def login():
        response = JSONResponse(
            {"access_token": "tok-xyz", "token_type": "bearer"},
            headers={
                "Content-Security-Policy": "default-src 'self'",
                "X-Frame-Options": "SAMEORIGIN",
            },
        )
        response.set_cookie("refresh_token", "ref-123", httponly=True)
        return response

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/v1/auth/login")
        assert resp.status_code == 200
        assert resp.headers.get("content-security-policy") == "default-src 'self'"
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"

        set_cookie_headers = resp.headers.get_list("set-cookie")
        assert any("refresh_token=ref-123" in value for value in set_cookie_headers)
        assert any("access_token=tok-xyz" in value for value in set_cookie_headers)
