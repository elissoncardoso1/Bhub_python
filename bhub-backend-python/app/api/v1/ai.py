"""
Rotas de IA (classificação e tradução).
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import get_ai_manager
from app.core.rate_limiting import get_user_id_for_rate_limit
from app.database import get_async_session
from app.main import limiter
from app.ml import EmbeddingClassifier, HeuristicClassifier
from app.services.translation_cache_service import (
    TranslationCacheService,
    generate_cache_key,
)

router = APIRouter(prefix="/ai", tags=["AI"])


class ClassifyRequest(BaseModel):
    """Request de classificação."""
    
    text: str = Field(..., min_length=10, max_length=10000)
    use_external: bool = Field(default=False, description="Usar IA externa")


class ClassifyResponse(BaseModel):
    """Resposta de classificação."""
    
    category: str
    confidence: float
    provider: str | None = None


class TranslateRequest(BaseModel):
    """Request de tradução."""
    
    text: str = Field(..., min_length=1, max_length=10000)
    source_lang: str = Field(default="en", max_length=10, description="Idioma de origem")
    target_lang: str = Field(default="pt-BR", max_length=10, description="Idioma de destino")


class TranslateResponse(BaseModel):
    """Resposta de tradução."""
    
    original: str
    translated: str
    provider: str | None = None
    cached: bool = Field(default=False, description="Indica se a tradução veio do cache")


@router.post("/classify", response_model=ClassifyResponse)
@limiter.limit("10/minute", key_func=get_user_id_for_rate_limit)
async def classify_text(request: Request, classify_request: ClassifyRequest):
    """Classifica texto em uma categoria."""
    
    if classify_request.use_external:
        # Usar IA externa
        ai_manager = get_ai_manager()
        category, confidence, provider = await ai_manager.classify(classify_request.text)
        
        return ClassifyResponse(
            category=category,
            confidence=confidence,
            provider=provider.value if provider else None,
        )
    
    # Usar ML local
    classifier = EmbeddingClassifier()
    
    if classifier.is_initialized():
        category, confidence = await classifier.classify(classify_request.text)
        provider = "local_ml"
    else:
        # Fallback para heurística
        category, confidence = HeuristicClassifier.classify(classify_request.text)
        provider = "heuristic"
    
    return ClassifyResponse(
        category=category,
        confidence=confidence,
        provider=provider,
    )


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit("10/minute", key_func=get_user_id_for_rate_limit)
async def translate_text(
    http_request: Request,
    request: TranslateRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Traduz texto para o idioma alvo com cache inteligente.
    
    O sistema verifica primeiro se existe uma tradução em cache antes
    de chamar a API externa, reduzindo custos e melhorando performance.
    """
    from app.core.logging import log
    
    # Gerar chave de cache
    cache_key = generate_cache_key(
        text=request.text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        model_version="deepseek-chat",  # Versão do modelo
    )
    
    # Verificar cache
    cached_translation = await TranslationCacheService.get_cached_translation(
        session=session,
        cache_key=cache_key,
    )
    
    if cached_translation:
        # Atualizar timestamp de acesso
        await TranslationCacheService.update_access_time(
            session=session,
            cache_key=cache_key,
        )
        
        log.info(
            f"Tradução encontrada no cache: {cache_key[:8]}... "
            f"({request.source_lang} -> {request.target_lang})"
        )
        
        return TranslateResponse(
            original=request.text,
            translated=cached_translation.translated_text,
            provider=cached_translation.provider,
            cached=True,
        )
    
    # Cache miss - chamar API
    log.info(
        f"Cache miss - chamando API para tradução: "
        f"{request.source_lang} -> {request.target_lang}"
    )
    
    ai_manager = get_ai_manager()
    translated, provider = await ai_manager.translate(
        request.text,
        request.target_lang,
    )
    
    # Salvar no cache
    try:
        await TranslationCacheService.save_translation(
            session=session,
            cache_key=cache_key,
            original_text=request.text,
            translated_text=translated,
            source_language=request.source_lang,
            target_language=request.target_lang,
            model="deepseek-chat",
            provider=provider.value if provider else None,
        )
    except Exception as e:
        # Log mas não falha se não conseguir salvar no cache
        log.warning(f"Erro ao salvar tradução no cache: {e}")
    
    return TranslateResponse(
        original=request.text,
        translated=translated,
        provider=provider.value if provider else None,
        cached=False,
    )


@router.get("/status")
async def get_ai_status():
    """Retorna status dos provedores de IA."""
    
    ai_manager = get_ai_manager()
    classifier = EmbeddingClassifier()
    
    return {
        "ml_local": classifier.get_status(),
        "external_providers": ai_manager.get_status(),
    }
