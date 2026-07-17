"""
Rotas de contato.
"""

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import DBSession
from app.core.csrf import CSRFValid
from app.models import ContactMessage
from app.schemas import MessageResponse

router = APIRouter(prefix="/contact", tags=["Contact"])


class ContactRequest(BaseModel):
    """Request de mensagem de contato."""

    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    subject: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=10, max_length=5000)


@router.post("", response_model=MessageResponse)
async def send_contact_message(
    db: DBSession,
    data: ContactRequest,
    csrf_valid: CSRFValid = True,  # Validação CSRF
):
    """Envia mensagem de contato."""

    # Não coletamos IP/user-agent (princípio da necessidade, art. 6º III LGPD):
    # nenhum mecanismo antiabuso consome esses campos; o form já tem CSRF + rate limiting.
    message = ContactMessage(
        name=data.name,
        email=data.email,
        phone=data.phone,
        subject=data.subject,
        message=data.message,
    )

    db.add(message)
    await db.commit()

    return MessageResponse(
        message="Mensagem enviada com sucesso! Entraremos em contato em breve.",
        success=True,
    )
