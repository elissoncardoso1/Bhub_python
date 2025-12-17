"""
Rotas de contato.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import DBSession
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
    request: Request,
    data: ContactRequest,
):
    """Envia mensagem de contato."""
    
    # Capturar metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Criar mensagem
    message = ContactMessage(
        name=data.name,
        email=data.email,
        phone=data.phone,
        subject=data.subject,
        message=data.message,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
    )
    
    db.add(message)
    await db.commit()
    
    return MessageResponse(
        message="Mensagem enviada com sucesso! Entraremos em contato em breve.",
        success=True,
    )
