"""
Rotas para tradução de conteúdo via HTMX.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.ai.manager import get_ai_manager
from app.api.deps import DBSession
from app.core.security import CurrentUserOptional
from app.services.translation_cache_service import (
    TranslationCacheService,
    generate_cache_key,
)
from app.web.templating import get_templates

router = APIRouter()


class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "pt"
    element_id: str | None = None  # ID do elemento HTML para trocar (opcional)
    article_id: int | None = None  # ID do artigo para persistência


@router.post("/translate")
async def translate_content(
    request: Request,
    translation_req: TranslationRequest,
    db: DBSession,
    current_user: CurrentUserOptional = None,
):
    """
    Endpoint HTMX para traduzir conteúdo sob demanda.
    Retorna o HTML traduzido do conteúdo.
    """
    templates = get_templates()

    if not translation_req.text:
        return ""

    try:
        # 1. Gerar chave de cache
        model_version = "deepseek-translator-v2"
        cache_key = generate_cache_key(
            translation_req.text,
            translation_req.source_lang,
            translation_req.target_lang,
            model_version
        )

        # 2. Verificar cache
        cached = await TranslationCacheService.get_cached_translation(db, cache_key)
        if cached:
            await TranslationCacheService.update_access_time(db, cache_key)
            translated_text = cached.translated_text
            is_cached = True
        else:
            # 3. Se não tiver no cache, chamar IA
            ai_manager = get_ai_manager()
            translated_text, provider = await ai_manager.translate(
                translation_req.text,
                translation_req.target_lang
            )

            # 4. Salvar no cache
            await TranslationCacheService.save_translation(
                db,
                cache_key,
                translation_req.text,
                translated_text,
                translation_req.source_lang,
                translation_req.target_lang,
                model_version,
                provider.value if provider else "unknown"
            )
            is_cached = False

        # 5. Persistir no Artigo se article_id for fornecido
        if translation_req.article_id:
            from sqlalchemy import update

            from app.models import Article

            # Atualiza o abstract_translated do artigo
            stmt = (
                update(Article)
                .where(Article.id == translation_req.article_id)
                .values(abstract_translated=translated_text)
            )
            await db.execute(stmt)
            await db.commit()

        # 6. Renderizar resposta (Success)
        return templates.TemplateResponse(
            "partials/translation_result.html",
            {
                "request": request,
                "translated_text": translated_text,
                "is_cached": is_cached,
                "element_id": translation_req.element_id,
            },
        )
    except Exception as e:
        import logging
        logging.error(f"Erro na tradução: {e}")
        return templates.TemplateResponse(
            "partials/translation_result.html",
            {
                "request": request,
                "error": str(e),
                "element_id": translation_req.element_id,
                "original_text": translation_req.text,
            },
        )
