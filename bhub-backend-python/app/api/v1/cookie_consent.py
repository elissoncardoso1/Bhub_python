"""Leitura do estado de consentimento (JSON)."""

from fastapi import APIRouter, Request, Response

from app.core.cookie_consent import get_consent

router = APIRouter(prefix="/cookie-consent", tags=["Cookie Consent"])


@router.get("")
async def get_cookie_consent(request: Request, response: Response) -> dict[str, object]:
    """Retorna as preferências atuais do visitante (sem dados pessoais)."""
    response.headers["Cache-Control"] = "no-store"
    return get_consent(request).as_dict()
