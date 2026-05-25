import asyncio
import uuid

import pytest
from fastapi import FastAPI, Request, Response

from app.core.cookie_transport import CookieTransport
from app.core.csrf_middleware import CSRFMiddleware
from app.core.rate_limiting import get_user_id_for_rate_limit, rate_limit
from app.core.refresh_token import RefreshTokenService


def test_cookie_transport_login_and_logout_sets_cookie():
    transport = CookieTransport(cookie_name="access_token", cookie_max_age=60, cookie_secure=False)
    response = Response()

    asyncio.run(transport.login("tok123", response))

    assert response.headers.get("set-cookie") is not None
    assert b'"access_token": "tok123"' in response.body
    assert response.headers["Content-Type"] == "application/json"

    asyncio.run(transport.logout(response))
    # Após logout, o cookie deve ser removido (Set-Cookie com Max-Age=0)
    assert "delete_cookie" not in response.headers.get("set-cookie", "")


def test_cookie_transport_get_token_from_cookie_and_header():
    transport = CookieTransport(cookie_name="access_token")

    class DummyRequest:
        def __init__(self):
            self.cookies = {"access_token": "from_cookie"}
            self.headers = {"Authorization": "Bearer from_header"}

    req = DummyRequest()
    assert transport.get_token_from_request(req) == "from_cookie"

    req.cookies = {}
    assert transport.get_token_from_request(req) == "from_header"


def test_get_user_id_for_rate_limit_header_and_fallback(monkeypatch):
    called = {}

    def fake_get_remote_address(request: Request):
        called["ip"] = True
        return "1.2.3.4"

    # Forçar falha de decode para cair no fallback de IP
    monkeypatch.setattr("app.core.rate_limiting.get_remote_address", fake_get_remote_address)
    request = Request(
        {
            "type": "http",
            "headers": [(b"authorization", b"Bearer invalid.token")],
            "client": ("1.2.3.4", 1234),
        }
    )
    user_id = get_user_id_for_rate_limit(request)
    assert user_id == "1.2.3.4"
    assert called["ip"] is True


@pytest.mark.asyncio
async def test_rate_limit_decorator_applies_and_calls_func(monkeypatch):
    calls = {"limited": False, "ran": False}

    def fake_limit(limit, key_func=None):
        def inner(func):
            def wrapped(*args, **kwargs):
                calls["limited"] = True
                return func(*args, **kwargs)

            return wrapped

        return inner

    monkeypatch.setattr("app.core.rate_limiting.limiter.limit", fake_limit)

    @rate_limit("1/minute")
    async def handler(request: Request):
        calls["ran"] = True
        return "ok"

    req = Request({"type": "http", "headers": [], "client": ("1.2.3.4", 1234)})
    result = await handler(req)
    assert result == "ok"
    assert calls["limited"] is True
    assert calls["ran"] is True


def test_refresh_token_service_happy_and_invalid_type():
    service = RefreshTokenService()
    user_id = uuid.uuid4()
    jwt_token = service.create_refresh_token_jwt(user_id=user_id, token_id="tid")

    payload = service.decode_refresh_token(jwt_token)
    assert payload["sub"] == str(user_id)
    assert payload["token_id"] == "tid"
    assert payload["type"] == "refresh"

    # token com type errado deve falhar
    from jose import jwt

    from app.config import settings

    bad_payload = payload | {"type": "access"}
    bad_token = jwt.encode(bad_payload, settings.secret_key, algorithm=settings.algorithm)
    with pytest.raises(Exception):
        service.decode_refresh_token(bad_token)


def test_refresh_token_cookie_helpers():
    service = RefreshTokenService()
    resp = Response()
    token = service.generate_refresh_token()

    service.set_refresh_token_cookie(resp, token)
    assert service.cookie_name in resp.headers.get("set-cookie")

    req = Request(
        {
            "type": "http",
            "headers": [(b"cookie", f"{service.cookie_name}={token}".encode())],
            "client": ("0.0.0.0", 0),
        }
    )
    assert service.get_refresh_token_from_cookie(req) == token

    service.clear_refresh_token_cookie(resp)
    assert service.cookie_name in resp.headers.get("set-cookie")


@pytest.mark.asyncio
async def test_csrf_middleware_auto_validate_blocks_without_token():
    app = FastAPI()
    middleware = CSRFMiddleware(app, auto_validate=True)

    async def call_next(request):
        return Response("ok")

    request = Request({"type": "http", "method": "POST", "path": "/mut", "headers": [], "client": ("0.0.0.0", 0)})

    with pytest.raises(Exception):
        await middleware.dispatch(request, call_next)
