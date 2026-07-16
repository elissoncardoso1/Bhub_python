"""
Rotas SSR de consentimento de cookies. Forms HTML puros (funcionam sem JS).
"""

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

from app.core.analytics_middleware import ANALYTICS_SESSION_COOKIE
from app.core.cookie_consent import (
    OPTIONAL_CATEGORIES,
    clear_consent_cookie,
    set_consent_cookie,
)
from app.core.csrf import CSRFValid

router = APIRouter(tags=["Cookie Consent"])

_ACTIONS = {"accept_all", "reject_all", "save", "revoke"}


def _safe_next(next_path: str | None) -> str:
    """Aceita apenas caminho relativo interno (anti open-redirect)."""
    if (
        next_path
        and next_path.startswith("/")
        and not next_path.startswith("//")
        and "\\" not in next_path
        and not any(ord(c) < 0x20 for c in next_path)
    ):
        return next_path
    return "/"


@router.post("/cookie-consent")
async def submit_cookie_consent(
    _csrf_valid: CSRFValid,
    action: str = Form(...),
    next_path: str | None = Form(default=None, alias="next"),
    analytics: str | None = Form(default=None),
    external_media: str | None = Form(default=None),
    marketing: str | None = Form(default=None),
) -> RedirectResponse:
    """Grava/revoga a escolha e redireciona de volta (303 See Other)."""
    if action not in _ACTIONS:
        raise HTTPException(status_code=400, detail="Ação de consentimento inválida.")

    response = RedirectResponse(url=_safe_next(next_path), status_code=303)

    if action == "revoke":
        clear_consent_cookie(response)
        # Apaga o cookie de sessão já existente; isso é só metade da garantia de
        # "parar coleta" — o gate que impede o AnalyticsMiddleware de emitir um
        # cookie *novo* sem consentimento é implementado em task seguinte.
        response.delete_cookie(ANALYTICS_SESSION_COOKIE, path="/")
        return response

    if action == "accept_all":
        preferences = dict.fromkeys(OPTIONAL_CATEGORIES, True)
    elif action == "reject_all":
        preferences = dict.fromkeys(OPTIONAL_CATEGORIES, False)
    else:  # save — checkbox marcada envia "on"; ausente = False
        submitted = {"analytics": analytics, "external_media": external_media, "marketing": marketing}
        preferences = {cat: submitted[cat] is not None for cat in OPTIONAL_CATEGORIES}

    set_consent_cookie(response, preferences)

    # Sem autorização de analytics, apagamos o cookie de sessão existente — mas
    # isso é só metade da garantia de "parar coleta". A outra metade (impedir o
    # AnalyticsMiddleware de recriar o cookie na próxima requisição sem
    # consentimento) depende do gate de consentimento nele, feito em task seguinte.
    if not preferences["analytics"]:
        response.delete_cookie(ANALYTICS_SESSION_COOKIE, path="/")

    return response
