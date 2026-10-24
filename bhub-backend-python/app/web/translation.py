"""
Rotas para tradução de conteúdo via HTMX.
"""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import update

from app.ai.manager import get_ai_manager
from app.api.deps import DBSession
from app.config import settings
from app.core.limiter import limiter
from app.models import Article
from app.services.translation_cache_service import (
    TranslationCacheService,
    generate_cache_key,
)
from app.web.templating import get_templates

router = APIRouter()

SOURCE_LANG = "en"
TARGET_LANG = "pt"
MODEL_VERSION = "deepseek-translator-v2"


class TranslationRequest(BaseModel):
    # O texto vem sempre do banco (abstract do artigo), nunca do cliente:
    # aceitar texto do cliente permitia gravar qualquer coisa em qualquer artigo.
    article_id: int
    element_id: str | None = None  # ID do elemento HTML para trocar (opcional)


@router.post("/translate")
@limiter.limit(settings.ai_rate_limit_daily)
@limiter.limit("10/minute")
async def translate_content(
    # slowapi exige um parâmetro chamado `request` do tipo Request.
    request: Request,
    translation_req: TranslationRequest,
    db: DBSession,
):
    """
    Endpoint HTMX para traduzir o resumo de um artigo sob demanda.
    Retorna o HTML traduzido do conteúdo.
    """
    templates = get_templates()
    error_context = {"request": request, "element_id": translation_req.element_id}

    article = await db.get(Article, translation_req.article_id)
    if not article or not article.abstract:
        return templates.TemplateResponse(
            "partials/translation_result.html",
            {**error_context, "error": "Resumo não disponível para tradução."},
        )
    text = article.abstract
    # Em caso de erro, o resumo original continua visível acima da mensagem.
    error_context["original_text"] = text

    try:
        cache_key = generate_cache_key(text, SOURCE_LANG, TARGET_LANG, MODEL_VERSION)

        cached = await TranslationCacheService.get_cached_translation(db, cache_key)
        if cached:
            await TranslationCacheService.update_access_time(db, cache_key)
            translated_text = cached.translated_text
            is_cached = True
        else:
            translated_text, provider = await get_ai_manager().translate(text, TARGET_LANG)
            # Sem provedor = todos falharam e o "resultado" é o texto original.
            # Não gravar: senão o original vira tradução permanente e o botão some.
            if provider is None:
                return templates.TemplateResponse(
                    "partials/translation_result.html",
                    {
                        **error_context,
                        "error": "Tradução indisponível no momento. Tente novamente.",
                    },
                )
            await TranslationCacheService.save_translation(
                db,
                cache_key,
                text,
                translated_text,
                SOURCE_LANG,
                TARGET_LANG,
                MODEL_VERSION,
                provider.value,
            )
            is_cached = False

        await db.execute(
            update(Article)
            .where(Article.id == article.id)
            .values(abstract_translated=translated_text)
        )
        await db.commit()

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
        logging.error(f"Erro na tradução do artigo {article.id}: {e}")
        return templates.TemplateResponse(
            "partials/translation_result.html",
            {**error_context, "error": "Tradução indisponível no momento. Tente novamente."},
        )
