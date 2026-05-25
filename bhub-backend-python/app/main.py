"""
Aplicação principal FastAPI - BHUB Backend.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth_router, users_router, v1_router
from app.config import settings
from app.core.access_token_cookie_middleware import AccessTokenCookieMiddleware
from app.core.analytics_middleware import AnalyticsMiddleware
from app.core.auth_cookie_middleware import AuthCookieMiddleware
from app.core.limiter import limiter
from app.core.logging import log, setup_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.database import close_db, init_db
from app.jobs import setup_scheduler, start_scheduler, stop_scheduler
from app.schemas import ErrorResponse, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    setup_logging()
    log.info(f"Iniciando {settings.app_name} v{settings.app_version}")

    if settings.enable_telemetry:
        from app.core.telemetry import setup_telemetry

        setup_telemetry(settings.telemetry_service_name)
        log.info("OpenTelemetry configurado")

    # Inicializar banco
    await init_db()
    log.info("Banco de dados inicializado")

    # Inicializar categorias padrão
    await seed_categories()

    # Configurar e iniciar scheduler
    setup_scheduler()
    start_scheduler()

    # Pré-aquecer ARQ quando habilitado. Em desenvolvimento/teste o dispatcher
    # usa fallback local se Redis/ARQ não estiverem disponíveis.
    if settings.enable_arq:
        try:
            from app.services.task_dispatcher import get_arq_pool

            await get_arq_pool()
            log.info("ARQ pool conectado")
        except Exception as e:
            log.warning(f"ARQ não inicializado: {e}")

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
    try:
        from app.services.task_dispatcher import close_arq_pool

        await close_arq_pool()
    except Exception as e:
        log.warning(f"Erro ao fechar ARQ pool: {e}")
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

# CSRF Middleware (gera tokens CSRF automaticamente)
from app.core.csrf_middleware import CSRFMiddleware

app.add_middleware(CSRFMiddleware, auto_validate=False)  # Validação manual via dependência

# Auth Cookie Middleware (adiciona cookies HttpOnly em login)
app.add_middleware(AuthCookieMiddleware)

# Compatibilidade: cookie `access_token` -> Authorization header
app.add_middleware(AccessTokenCookieMiddleware)

# Analytics Middleware (deve vir antes do CORS)
if settings.enable_analytics:
    app.add_middleware(
        AnalyticsMiddleware,
        enabled=settings.enable_analytics,
    )

# CORS
# Headers permitidos explicitamente (segurança)
allowed_headers = [
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    # HTMX
    "HX-Request",
    "HX-Trigger",
    "HX-Trigger-Name",
    "HX-Target",
    "HX-Current-URL",
    "Accept",
    "Origin",
    "X-Session-ID",  # Para analytics
    "X-Cron-Secret",  # Para cron endpoint
    "X-CSRF-Token",  # Para proteção CSRF
]

# Métodos permitidos explicitamente
allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# Em desenvolvimento, permitir qualquer origem local (localhost ou IP local)
if settings.is_development:
    # Permitir localhost e IPs locais (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    # Regex para match de IPs locais e localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+):\d+$",
        allow_credentials=True,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
    )
else:
    # Em produção, usar apenas origens permitidas explicitamente
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
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

    wants_html = request.headers.get("hx-request") == "true" or "text/html" in request.headers.get(
        "accept", ""
    )

    if wants_html and not request.url.path.startswith("/api"):
        from app.core.csrf import get_csrf_token
        from app.web.templating import get_templates

        templates = get_templates()
        csrf_token = await get_csrf_token(request)
        return templates.TemplateResponse(
            "pages/error.html",
            {
                "request": request,
                "title": "Erro",
                "csrf_token": csrf_token,
                "static_version": f"{settings.app_version}",
                "current_user": None,
                "message": "Erro interno do servidor",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="Erro interno do servidor",
            code="INTERNAL_ERROR",
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para HTTPException com suporte a HTML em rotas web."""
    wants_html = request.headers.get("hx-request") == "true" or "text/html" in request.headers.get(
        "accept", ""
    )

    # Para a API, manter JSON padrão.
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    # UX: redirecionar para login ao tentar acessar admin sem auth (mesmo sem Accept HTML).
    if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN) and request.url.path.startswith(
        "/admin"
    ):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_303_SEE_OTHER)

    if not wants_html:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    from app.core.csrf import get_csrf_token
    from app.web.templating import get_templates

    templates = get_templates()
    csrf_token = await get_csrf_token(request)

    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return templates.TemplateResponse(
            "pages/not_found.html",
            {
                "request": request,
                "title": "Não encontrado",
                "csrf_token": csrf_token,
                "static_version": f"{settings.app_version}",
                "current_user": None,
            },
            status_code=exc.status_code,
        )

    return templates.TemplateResponse(
        "pages/error.html",
        {
            "request": request,
            "title": "Erro",
            "csrf_token": csrf_token,
            "static_version": f"{settings.app_version}",
            "current_user": None,
            "message": str(exc.detail) if exc.detail else "Ocorreu um erro ao processar sua solicitação.",
        },
        status_code=exc.status_code,
    )


# Incluir routers
from app.web.router import router as web_router

app.mount(
    "/static",
    StaticFiles(directory=str(settings.base_dir / "app" / "static")),
    name="static",
)

app.include_router(web_router)
app.include_router(v1_router)
app.include_router(auth_router)
app.include_router(users_router)


# Rotas utilitárias
@app.get("/api", tags=["Root"])
async def api_root():
    """Rota raiz da API."""
    return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs" if settings.debug else None}


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
@limiter.limit("3/hour")  # Rate limiting muito restritivo para prevenir brute force
async def cron_sync(request: Request):
    """Endpoint para sincronização via cron externo."""

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
