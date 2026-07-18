"""
Consentimento de cookies (LGPD) — fonte única de parsing/validação do cookie
`bhub_consent`. Nenhum outro módulo deve interpretar o cookie manualmente.

O cookie guarda apenas flags booleanas por categoria + versão + timestamp.
Nunca armazenar: nome, e-mail, IP, id de usuário, fingerprint ou token.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request, Response

from app.config import settings

CONSENT_COOKIE_NAME = "bhub_consent"
CONSENT_COOKIE_MAX_AGE = 180 * 24 * 3600  # 180 dias
_MAX_COOKIE_BYTES = 1024

# Categorias opcionais (a "necessary" é fixa e não desativável)
OPTIONAL_CATEGORIES = ("analytics", "external_media", "marketing")


@dataclass(frozen=True)
class ConsentState:
    """Estado de consentimento do visitante (imutável)."""

    analytics: bool = False
    external_media: bool = False
    marketing: bool = False
    version: str | None = None
    updated_at: str | None = None
    decided: bool = False  # True apenas com cookie válido na versão atual

    @property
    def necessary(self) -> bool:
        return True

    def as_dict(self) -> dict[str, object]:
        # `updated_at` fica de fora intencionalmente: este dict alimenta
        # templates/API e o timestamp não é relevante para essas consumidoras.
        return {
            "necessary": True,
            "analytics": self.analytics,
            "external_media": self.external_media,
            "marketing": self.marketing,
            "version": self.version,
            "decided": self.decided,
        }


_UNDECIDED = ConsentState()


def parse_consent_cookie(raw: str | None) -> ConsentState:
    """Interpreta o cookie com validação estrita; qualquer anomalia → estado seguro."""
    if not raw or len(raw.encode("utf-8", errors="replace")) > _MAX_COOKIE_BYTES:
        return _UNDECIDED
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _UNDECIDED
    if not isinstance(data, dict):
        return _UNDECIDED

    for category in OPTIONAL_CATEGORIES:
        if not isinstance(data.get(category), bool):
            return _UNDECIDED
    version = data.get("version")
    if not isinstance(version, str):
        return _UNDECIDED

    # Renovar a escolha quando a versão da política mudar
    if version != settings.cookie_consent_version:
        return _UNDECIDED

    updated_at = data.get("updated_at")
    return ConsentState(
        analytics=data["analytics"],
        external_media=data["external_media"],
        marketing=data["marketing"],
        version=version,
        updated_at=updated_at if isinstance(updated_at, str) else None,
        decided=True,
    )


def get_consent(request: Request) -> ConsentState:
    """Estado de consentimento da requisição atual."""
    return parse_consent_cookie(request.cookies.get(CONSENT_COOKIE_NAME))


def is_granted(request: Request, category: str) -> bool:
    """True se a categoria foi autorizada. `necessary` é sempre True."""
    if category == "necessary":
        return True
    if category not in OPTIONAL_CATEGORIES:
        return False
    state = get_consent(request)
    return state.decided and bool(getattr(state, category, False))


def serialize_consent(preferences: dict[str, bool]) -> str:
    """Serializa preferências (apenas categorias conhecidas; necessary forçada)."""
    payload = {
        "necessary": True,
        **{cat: bool(preferences.get(cat, False)) for cat in OPTIONAL_CATEGORIES},
        "version": settings.cookie_consent_version,
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    return json.dumps(payload, separators=(",", ":"))


def set_consent_cookie(response: Response, preferences: dict[str, bool]) -> None:
    """Grava a escolha em cookie essencial (HttpOnly; estado é renderizado pelo servidor)."""
    response.set_cookie(
        key=CONSENT_COOKIE_NAME,
        value=serialize_consent(preferences),
        max_age=CONSENT_COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        path="/",
    )


def clear_consent_cookie(response: Response) -> None:
    """Revoga o consentimento (o banner voltará a aparecer)."""
    response.delete_cookie(CONSENT_COOKIE_NAME, path="/")
