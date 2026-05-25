"""
Testes unitários do CSRFProtection para cobrir cenários de tokens.
"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.csrf import csrf_protection


def make_request(method: str, path: str = "/test", headers=None) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
    }
    return Request(scope)


def test_csrf_missing_cookie_raises():
    req = make_request("POST")
    with pytest.raises(HTTPException) as exc:
        csrf_protection.validate_csrf(req, require_token=True)
    assert exc.value.status_code == 403


def test_csrf_missing_header_raises():
    req = make_request(
        "POST",
        headers=[(b"cookie", b"csrf_token=abc")],
    )
    with pytest.raises(HTTPException) as exc:
        csrf_protection.validate_csrf(req, require_token=True)
    assert exc.value.status_code == 403


def test_csrf_mismatched_tokens_raises():
    req = make_request(
        "POST",
        headers=[
            (b"cookie", b"csrf_token=abc"),
            (b"x-csrf-token", b"xyz"),
        ],
    )
    with pytest.raises(HTTPException) as exc:
        csrf_protection.validate_csrf(req, require_token=True)
    assert exc.value.status_code == 403


def test_csrf_valid_tokens_pass():
    req = make_request(
        "POST",
        headers=[
            (b"cookie", b"csrf_token=abc"),
            (b"x-csrf-token", b"abc"),
        ],
    )
    assert csrf_protection.validate_csrf(req, require_token=True) is True


def test_csrf_safe_methods_allowed():
    for method in ("GET", "HEAD", "OPTIONS"):
        req = make_request(method)
        assert csrf_protection.validate_csrf(req, require_token=True) is True
