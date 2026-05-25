import pytest
from starlette.requests import Request

from app.web.auth import login_page, sanitize_next_url


class AdminUser:
    is_admin = True


class RegularUser:
    is_admin = False


@pytest.mark.asyncio
async def test_login_page_redirects_admin():
    request = Request({"type": "http", "headers": [], "client": ("0.0.0.0", 0), "path": "/login"})
    response = await login_page(request, current_user=AdminUser(), next_url="/admin")
    assert response.status_code == 303
    assert response.headers.get("location") == "/admin"


@pytest.mark.asyncio
async def test_login_page_redirects_regular():
    request = Request({"type": "http", "headers": [], "client": ("0.0.0.0", 0), "path": "/login"})
    response = await login_page(request, current_user=RegularUser(), next_url=None)
    assert response.status_code == 303
    assert response.headers.get("location") == "/"


@pytest.mark.asyncio
async def test_login_page_rejects_open_redirect_for_admin():
    request = Request({"type": "http", "headers": [], "client": ("0.0.0.0", 0), "path": "/login"})
    response = await login_page(
        request,
        current_user=AdminUser(),
        next_url="https://attacker.example/path",
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/admin"


@pytest.mark.asyncio
async def test_login_page_rejects_open_redirect_for_regular_user():
    request = Request({"type": "http", "headers": [], "client": ("0.0.0.0", 0), "path": "/login"})
    response = await login_page(
        request,
        current_user=RegularUser(),
        next_url="//attacker.example/path",
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/"


@pytest.mark.parametrize(
    ("next_url", "is_admin", "expected"),
    [
        ("/admin/dashboard", True, "/admin/dashboard"),
        ("https://evil.test", True, "/admin"),
        ("//evil.test", True, "/admin"),
        ("/articles", False, "/articles"),
        ("https://evil.test", False, "/"),
    ],
)
def test_sanitize_next_url(next_url: str, is_admin: bool, expected: str):
    assert sanitize_next_url(next_url, is_admin=is_admin) == expected
