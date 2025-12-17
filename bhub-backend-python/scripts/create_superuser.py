
import asyncio
import sys
import os
from getpass import getpass

# Adicionar raiz no path
sys.path.insert(0, os.getcwd())

from app.database import get_session_context
from app.core.security import get_user_manager
from app.schemas.user import UserCreate
from app.models.user import User, UserRole

async def create_superuser():
    print("--- Criar Superusuário ---")
    email = input("Email: ").strip()
    if not email:
        print("Email é obrigatório.")
        return

    password = getpass("Senha: ").strip()
    if not password:
        print("Senha é obrigatória.")
        return
    
    confirm = getpass("Confirme a senha: ").strip()
    if password != confirm:
        print("As senhas não conferem.")
        return

    async with get_session_context() as session:
        # Mock do user_db adapter
        from fastapi_users.db import SQLAlchemyUserDatabase
        user_db = SQLAlchemyUserDatabase(session, User)
        
        # Instanciar user manager
        # UserManager espera user_db
        from app.core.security import UserManager
        user_manager = UserManager(user_db)
        
        try:
            user_create = UserCreate(
                email=email,
                password=password,
                is_superuser=True,
                is_active=True,
                is_verified=True,
                role=UserRole.ADMIN,
                name="System Administrator" 
            )
            
            # create é método do BaseUserManager
            user = await user_manager.create(user_create)
            print(f"\nSucesso! Usuário {user.email} criado com privilégios de administrador.")
            print(f"ID: {user.id}")
            
        except Exception as e:
            print(f"\nErro ao criar usuário: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(create_superuser())
    except KeyboardInterrupt:
        print("\nOperação cancelada.")
