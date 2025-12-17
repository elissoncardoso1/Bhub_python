"""
Rotas de autenticação.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DBSession
from app.core.refresh_token import (
    refresh_token_service,
    validate_and_refresh_token,
)
from app.core.security import auth_backend, fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# Rotas de login/logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
)

# Rotas de registro
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

# Rotas de reset de senha
router.include_router(
    fastapi_users.get_reset_password_router(),
)

# Rotas de verificação
router.include_router(
    fastapi_users.get_verify_router(UserRead),
)

# Rota customizada de login com refresh token
@router.post("/login")
async def login_with_refresh_token(
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: DBSession = Depends(),
    request: Request = None,
    response: Response = None,
):
    """
    Login customizado que retorna access token e refresh token.
    """
    from app.core.security import get_user_manager
    
    # Obter user manager
    async for manager in get_user_manager():
        user_manager = manager
        break
    
    # Autenticar usuário
    user = await user_manager.authenticate(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    
    # Gerar access token
    from app.core.security import get_jwt_strategy
    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token({"sub": str(user.id)})
    
    # Gerar refresh token
    refresh_token, _ = await refresh_token_service.create_refresh_token(db, user)
    
    # Definir cookies
    refresh_token_service.set_refresh_token_cookie(response, refresh_token)
    
    # Atualizar último login
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# Rota de refresh token
@router.post("/refresh")
async def refresh_access_token(
    user_and_token: tuple = Depends(validate_and_refresh_token),
    response: Response = None,
):
    """
    Atualiza access token usando refresh token.
    """
    user, new_access_token = user_and_token
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


# Rota de logout
@router.post("/logout")
async def logout(response: Response):
    """
    Logout que remove refresh token.
    """
    refresh_token_service.clear_refresh_token_cookie(response)
    return {"message": "Logout realizado com sucesso"}


# Rotas de gerenciamento de usuário
users_router = APIRouter(prefix="/api/v1/users", tags=["Users"])
users_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)

__all__ = ["router", "users_router"]
