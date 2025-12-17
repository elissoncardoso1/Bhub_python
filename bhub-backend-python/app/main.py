"""
Aplicação principal FastAPI - BHUB Backend.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import auth_router, users_router, v1_router
from app.config import settings
from app.core.analytics_middleware import AnalyticsMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.logging import log, setup_logging
from app.database import close_db, init_db
from app.jobs import setup_scheduler, start_scheduler, stop_scheduler
from app.schemas import ErrorResponse, HealthResponse


# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    setup_logging()
    log.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    
    # Inicializar banco
    await init_db()
    log.info("Banco de dados inicializado")
    
    # Inicializar categorias padrão
    await seed_categories()
    
    # Configurar e iniciar scheduler
    setup_scheduler()
    start_scheduler()
    
    # Inicializar ML (em background)
    try:
        from app.ml import EmbeddingClassifier
        await EmbeddingClassifier.initialize()
        
        # Carregar embeddings das categorias
        from app.models import DEFAULT_CATEGORIES
        await EmbeddingClassifier.load_category_embeddings(DEFAULT_CATEGORIES)
    except Exception as e:
        log.warning(f"ML não inicializado: {e}")
    
    log.info("Aplicação iniciada com sucesso")
    
    yield
    
    # Shutdown
    log.info("Encerrando aplicação...")
    stop_scheduler()
    await close_db()
    log.info("Aplicação encerrada")


async def seed_categories():
    """Popula categorias padrão se não existirem."""
    from sqlalchemy import select
    
    from app.database import get_session_context
    from app.models import DEFAULT_CATEGORIES, Category
    
    async with get_session_context() as db:
        result = await db.execute(select(Category))
        existing = result.scalars().all()
        
        if not existing:
            log.info("Criando categorias padrão...")
            for cat_data in DEFAULT_CATEGORIES:
                category = Category(**cat_data)
                db.add(category)
            await db.commit()
            log.info(f"{len(DEFAULT_CATEGORIES)} categorias criadas")


# Criar aplicação
app = FastAPI(
    title=settings.app_name,
    description="API de agregação e análise de artigos científicos em Análise do Comportamento",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Headers Middleware (deve vir primeiro)
app.add_middleware(SecurityHeadersMiddleware)

# Analytics Middleware (deve vir antes do CORS)
if settings.enable_analytics:
    app.add_middleware(
        AnalyticsMiddleware,
        enabled=settings.enable_analytics,
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação."""
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(l) for l in error["loc"])
        errors.append(f"{loc}: {error['msg']}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail="; ".join(errors),
            code="VALIDATION_ERROR",
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas."""
    log.error(f"Erro não tratado: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="Erro interno do servidor",
            code="INTERNAL_ERROR",
        ).model_dump(),
    )


# Incluir routers
app.include_router(v1_router)
app.include_router(auth_router)
app.include_router(users_router)


# Rotas utilitárias
@app.get("/", tags=["Root"])
async def root():
    """Rota raiz."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check da aplicação."""
    from app.ml import EmbeddingClassifier
    
    ml_status = "loaded" if EmbeddingClassifier.is_initialized() else "not_loaded"
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database="connected",
        ml_model=ml_status,
        timestamp=datetime.utcnow(),
    )


@app.post("/api/v1/cron/sync", tags=["Cron"])
async def cron_sync(request: Request):
    """Endpoint para sincronização via cron externo."""
    from app.api.deps import verify_cron_secret
    
    # Verificar secret
    cron_secret = request.headers.get("x-cron-secret")
    if not cron_secret or cron_secret != settings.cron_secret:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Cron secret inválido"},
        )
    
    # Executar sincronização
    from app.jobs import sync_all_feeds_job
    
    await sync_all_feeds_job()
    
    return {"success": True, "message": "Sincronização iniciada"}


# Para execução direta
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
