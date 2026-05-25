"""
Rotas web de autenticação (SSR).
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DBSession
from app.config import settings
from app.core.refresh_token import refresh_token_service
from app.core.security import CurrentUserOptional, UserManager, get_jwt_strategy, get_user_manager
from app.web.templating import get_templates

router = APIRouter(tags=["Web - Auth"])


def sanitize_next_url(next_url: str | None, *, is_admin: bool) -> str:
    """
    Sanitiza URL de redirecionamento pós-login.

    Permite apenas paths internos relativos ("/..."), sem schema/host.
    """
    fallback = "/admin" if is_admin else "/"
    if not next_url:
        return fallback

    candidate = next_url.strip()
    if not candidate:
        return fallback
    if not candidate.startswith("/") or candidate.startswith("//"):
        return fallback
    if "\\" in candidate:
        return fallback

    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return fallback
    return candidate


@router.get("/login")
async def login_page(
    request: Request,
    current_user: CurrentUserOptional = None,
    next_url: str | None = Query(default=None, alias="next"),
):
    if current_user:
        if current_user.is_admin:
            target = sanitize_next_url(next_url, is_admin=True)
            return RedirectResponse(url=target, status_code=303)
        return RedirectResponse(url="/", status_code=303)

    safe_next_url = sanitize_next_url(next_url, is_admin=True) if next_url else None

    templates = get_templates()
    from app.core.csrf import get_csrf_token

    csrf_token = await get_csrf_token(request)
    return templates.TemplateResponse(
        "pages/login.html",
        {
            "request": request,
            "title": "Entrar",
            "csrf_token": csrf_token,
            "static_version": f"{settings.app_version}",
            "current_user": current_user,
            "error": None,
            "next_url": safe_next_url,
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: DBSession,
    user_manager: UserManager = Depends(get_user_manager),
    credentials: OAuth2PasswordRequestForm = Depends(),
    next_url: str | None = Form(default=None, alias="next"),
):
    templates = get_templates()
    from app.core.csrf import get_csrf_token

    csrf_token = await get_csrf_token(request)
    safe_next_url = sanitize_next_url(next_url, is_admin=True) if next_url else None

    user = await user_manager.authenticate(credentials)
    if not user:
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "title": "Entrar",
                "csrf_token": csrf_token,
                "static_version": f"{settings.app_version}",
                "current_user": None,
                "error": "Credenciais inválidas.",
                "next_url": safe_next_url,
            },
            status_code=401,
        )

    if not user.is_admin:
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "title": "Entrar",
                "csrf_token": csrf_token,
                "static_version": f"{settings.app_version}",
                "current_user": None,
                "error": "Acesso negado. Requer permissão de administrador.",
                "next_url": safe_next_url,
            },
            status_code=403,
        )

    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)

    # Refresh token em cookie (opcional para SSR)
    refresh_token, _ = await refresh_token_service.create_refresh_token(db, user)

    response = RedirectResponse(
        url=sanitize_next_url(next_url, is_admin=True),
        status_code=303,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path="/",
    )
    refresh_token_service.set_refresh_token_cookie(response, refresh_token)

    user.last_login_at = datetime.utcnow()
    await db.commit()

    return response


@router.get("/logout")
async def logout(
    request: Request,
    db: DBSession,
):
    response = RedirectResponse(url="/", status_code=303)
    refresh_token = refresh_token_service.get_refresh_token_from_cookie(request)
    await refresh_token_service.revoke_refresh_token(db, refresh_token)
    response.delete_cookie(key="access_token", path="/")
    refresh_token_service.clear_refresh_token_cookie(response)
    return response
