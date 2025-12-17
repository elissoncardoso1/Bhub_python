"""
Sistema de refresh tokens para autenticação JWT.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import log
from app.database import get_async_session
from app.models.user import User


class RefreshTokenService:
    """Serviço para gerenciar refresh tokens."""

    def __init__(self):
        self.cookie_name = "refresh_token"
        self.token_length = 64

    def generate_refresh_token(self) -> str:
        """Gera um refresh token seguro."""
        return secrets.token_urlsafe(self.token_length)

    def create_refresh_token_jwt(
        self,
        user_id: uuid.UUID,
        token_id: str,
    ) -> str:
        """
        Cria um JWT para refresh token.
        
        Args:
            user_id: ID do usuário
            token_id: ID único do refresh token (para revogação)
        
        Returns:
            JWT token
        """
        expires_delta = timedelta(days=settings.refresh_token_expire_days)
        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(user_id),
            "token_id": token_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.algorithm,
        )

    def decode_refresh_token(self, token: str) -> dict:
        """
        Decodifica e valida refresh token.
        
        Returns:
            Payload do token
            
        Raises:
            HTTPException: Se token inválido
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )

            # Verificar tipo
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tipo de token inválido",
                )

            return payload
        except JWTError as e:
            log.warning(f"Erro ao decodificar refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado",
            )

    def set_refresh_token_cookie(
        self,
        response: Response,
        token: str,
    ) -> None:
        """Define o refresh token em um cookie HttpOnly."""
        max_age = settings.refresh_token_expire_days * 24 * 3600
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            httponly=True,
            secure=not settings.is_development,  # Secure apenas em produção
            samesite="strict",
            max_age=max_age,
            path="/",
        )

    def clear_refresh_token_cookie(self, response: Response) -> None:
        """Remove o refresh token do cookie."""
        response.delete_cookie(
            key=self.cookie_name,
            httponly=True,
            secure=not settings.is_development,
            samesite="strict",
            path="/",
        )

    def get_refresh_token_from_cookie(self, request: Request) -> Optional[str]:
        """Obtém o refresh token do cookie."""
        return request.cookies.get(self.cookie_name)

    async def create_refresh_token(
        self,
        db: AsyncSession,
        user: User,
    ) -> tuple[str, str]:
        """
        Cria um novo refresh token para o usuário.
        
        Returns:
            Tupla (refresh_token_jwt, token_id)
        """
        # Gerar ID único para o token
        token_id = secrets.token_urlsafe(32)
        
        # Criar JWT
        refresh_token = self.create_refresh_token_jwt(user.id, token_id)
        
        # TODO: Armazenar token_id no banco para permitir revogação
        # Por enquanto, apenas retornamos o token
        
        return refresh_token, token_id

    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> tuple[User, str]:
        """
        Valida refresh token e retorna novo access token.
        
        Returns:
            Tupla (user, new_access_token)
            
        Raises:
            HTTPException: Se token inválido
        """
        # Decodificar token
        payload = self.decode_refresh_token(refresh_token)
        
        user_id = uuid.UUID(payload["sub"])
        token_id = payload.get("token_id")
        
        # Buscar usuário
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado ou inativo",
            )
        
        # TODO: Verificar se token_id foi revogado (quando implementar blacklist)
        
        # Gerar novo access token
        from app.core.security import get_jwt_strategy
        
        jwt_strategy = get_jwt_strategy()
        access_token = await jwt_strategy.write_token({"sub": str(user.id)})
        
        return user, access_token


# Instância global
refresh_token_service = RefreshTokenService()


async def get_refresh_token_from_request(request: Request) -> Optional[str]:
    """Obtém refresh token da requisição."""
    return refresh_token_service.get_refresh_token_from_cookie(request)


async def validate_and_refresh_token(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> tuple[User, str]:
    """
    Dependência para validar refresh token e retornar novo access token.
    
    Usage:
        @router.post("/auth/refresh")
        async def refresh(
            user_and_token: Annotated[
                tuple[User, str],
                Depends(validate_and_refresh_token)
            ]
        ):
            user, new_token = user_and_token
            ...
    """
    refresh_token = refresh_token_service.get_refresh_token_from_cookie(request)
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token não encontrado",
        )
    
    return await refresh_token_service.refresh_access_token(db, refresh_token)

