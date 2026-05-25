"""
Sistema de refresh tokens para autenticação JWT.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import log
from app.database import get_async_session
from app.models.refresh_token import RefreshToken
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
            "jti": token_id,
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

    def _extract_token_id(self, payload: dict) -> str:
        """Extrai token_id/jti do payload."""
        token_id = payload.get("token_id") or payload.get("jti")
        if not token_id or not isinstance(token_id, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )
        return token_id

    def _extract_user_id(self, payload: dict) -> uuid.UUID:
        """Extrai user_id do payload."""
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )
        try:
            return uuid.UUID(sub)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
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

    def get_refresh_token_from_cookie(self, request: Request) -> str | None:
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
        token_id = secrets.token_urlsafe(32)
        refresh_token = self.create_refresh_token_jwt(user.id, token_id)
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        db_token = RefreshToken(
            token_id=token_id,
            user_id=user.id,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(db_token)
        await db.flush()

        return refresh_token, token_id

    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> tuple[User, str, str]:
        """
        Valida refresh token e retorna novo access token.

        Returns:
            Tupla (user, new_access_token, new_refresh_token)

        Raises:
            HTTPException: Se token inválido
        """
        payload = self.decode_refresh_token(refresh_token)
        user_id = self._extract_user_id(payload)
        token_id = self._extract_token_id(payload)

        token_record = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_id == token_id)
        )

        if not token_record or not token_record.is_active or token_record.revoked_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revogado ou inválido",
            )

        expires_at = token_record.expires_at
        if expires_at.tzinfo is not None:
            is_expired = expires_at <= datetime.now(expires_at.tzinfo)
        else:
            is_expired = expires_at <= datetime.utcnow()

        if is_expired:
            token_record.is_active = False
            token_record.revoked_at = datetime.utcnow()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado",
            )

        if str(token_record.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado ou inativo",
            )

        # Rotação: revoga token atual e emite novo refresh token.
        token_record.is_active = False
        token_record.revoked_at = datetime.utcnow()
        new_refresh_token, new_token_id = await self.create_refresh_token(db, user)
        token_record.replaced_by_token_id = new_token_id
        await db.flush()

        from app.core.security import get_jwt_strategy

        jwt_strategy = get_jwt_strategy()
        access_token = await jwt_strategy.write_token(user)

        return user, access_token, new_refresh_token

    async def revoke_refresh_token(
        self,
        db: AsyncSession,
        refresh_token: str | None,
    ) -> bool:
        """Revoga o refresh token atual, se existir."""
        if not refresh_token:
            return False

        try:
            payload = self.decode_refresh_token(refresh_token)
        except HTTPException:
            return False

        token_id = payload.get("token_id") or payload.get("jti")
        if not token_id or not isinstance(token_id, str):
            return False

        token_record = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_id == token_id)
        )
        if not token_record:
            return False

        if token_record.is_active or token_record.revoked_at is None:
            token_record.is_active = False
            token_record.revoked_at = datetime.utcnow()
            await db.flush()

        return True


# Instância global
refresh_token_service = RefreshTokenService()


async def get_refresh_token_from_request(request: Request) -> str | None:
    """Obtém refresh token da requisição."""
    return refresh_token_service.get_refresh_token_from_cookie(request)


async def validate_and_refresh_token(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> tuple[User, str, str]:
    """
    Dependência para validar refresh token e retornar novo access token.

    Usage:
        @router.post("/auth/refresh")
        async def refresh(
            user_and_token: Annotated[
                tuple[User, str, str],
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
