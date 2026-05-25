"""
Rotas de autenticação.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DBSession
from app.core.csrf import validate_csrf_if_present
from app.core.refresh_token import (
    refresh_token_service,
    validate_and_refresh_token,
)
from app.core.security import (
    UserManager,
    auth_backend,
    fastapi_users,
    get_jwt_strategy,
    get_user_manager,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Auth"],
    dependencies=[Depends(validate_csrf_if_present)],
)

# Rotas de login/logout (remover login padrão para usar login customizado com refresh)
auth_router = fastapi_users.get_auth_router(auth_backend)
auth_router.routes = [
    route
    for route in auth_router.routes
    if not (
        getattr(route, "path", "") in ("/login", "/logout")
        and "POST" in getattr(route, "methods", [])
    )
]
router.include_router(auth_router)

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
    request: Request,
    response: Response,
    db: DBSession,
    user_manager: UserManager = Depends(get_user_manager),
    credentials: OAuth2PasswordRequestForm = Depends(),
):
    """
    Login customizado que retorna access token e refresh token.
    """
    # Autenticar usuário
    user = await user_manager.authenticate(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    # Gerar access token
    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)

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
    response: Response,
    user_and_token: tuple[User, str, str] = Depends(validate_and_refresh_token),
):
    """
    Atualiza access token usando refresh token.
    """
    _user, new_access_token, new_refresh_token = user_and_token
    refresh_token_service.set_refresh_token_cookie(response, new_refresh_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


# Rota de logout
@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: DBSession,
):
    """
    Logout que remove refresh token.
    """
    refresh_token = refresh_token_service.get_refresh_token_from_cookie(request)
    await refresh_token_service.revoke_refresh_token(db, refresh_token)
    refresh_token_service.clear_refresh_token_cookie(response)
    return {"message": "Logout realizado com sucesso"}


# Rotas de gerenciamento de usuário
users_router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
    dependencies=[Depends(validate_csrf_if_present)],
)
users_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)

__all__ = ["router", "users_router"]
