"""
Rotas de Open Graph para geração dinâmica de meta tags e imagens.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select

from app.api.deps import DBSession
from app.config import settings
from app.models import Article
from app.services.opengraph_service import OpenGraphService

router = APIRouter(prefix="/og", tags=["Open Graph"])

# Instância global do serviço
og_service = OpenGraphService()


@router.get("/articles/{article_id}/meta")
async def get_article_og_meta(
    request: Request,
    db: DBSession,
    article_id: int,
):
    """
    Retorna metadados Open Graph para um artigo em formato HTML.

    Útil para crawlers que precisam das meta tags diretamente.
    """
    # Obter URL base
    base_url = str(request.base_url).rstrip("/")

    # Obter metadados
    metadata = await og_service.get_article_metadata(article_id, base_url)

    # Gerar HTML com meta tags
    meta_tags = []
    for key, value in metadata.items():
        if key.startswith("og:") or key.startswith("twitter:"):
            property_name = key.replace("og:", "property=").replace("twitter:", "name=")
            meta_tags.append(f'<meta {property_name}="{key}" content="{value}">')
        elif key in ["title", "description"]:
            meta_tags.append(f'<meta name="{key}" content="{value}">')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{metadata.get('title', 'BHub')}</title>
        {''.join(meta_tags)}
    </head>
    <body>
        <h1>{metadata.get('og:title', 'BHub')}</h1>
        <p>{metadata.get('og:description', '')}</p>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


@router.get("/articles/{article_id}/image")
async def get_article_og_image(
    db: DBSession,
    article_id: int,
):
    """
    Retorna imagem Open Graph para um artigo.

    Gera a imagem sob demanda se não existir em cache.
    """
    # Verificar se artigo existe
    result = await db.execute(
        select(Article).where(Article.id == article_id, Article.is_published == True)
    )
    article = result.scalar_one_or_none()

    if not article:
        # Retornar imagem padrão
        image_path = await og_service.generate_default_image()
    else:
        # Gerar imagem do artigo
        image_path = await og_service.generate_article_image(article)

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar imagem",
        )

    return FileResponse(
        path=image_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",  # Cache por 1 ano
        },
    )


@router.get("/default/image")
async def get_default_og_image():
    """Retorna imagem padrão Open Graph."""
    image_path = await og_service.generate_default_image()

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar imagem padrão",
        )

    return FileResponse(
        path=image_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )


@router.get("/articles/{article_id}/json")
async def get_article_og_json(
    request: Request,
    db: DBSession,
    article_id: int,
):
    """
    Retorna metadados Open Graph em formato JSON.

    Útil para consumo programático ou SSR no frontend.
    """
    base_url = str(request.base_url).rstrip("/")
    metadata = await og_service.get_article_metadata(article_id, base_url)

    return metadata


@router.post("/articles/{article_id}/regenerate")
async def regenerate_article_og_image(
    db: DBSession,
    article_id: int,
):
    """
    Força regeneração da imagem Open Graph de um artigo.

    Útil após atualizações no artigo.
    """
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artigo não encontrado",
        )

    # Remover cache existente
    cache_key = og_service._get_cache_key(article_id)
    cache_path = og_service.cache_dir / f"{cache_key}.png"
    if cache_path.exists():
        cache_path.unlink()

    # Regenerar
    image_path = await og_service.generate_article_image(article)

    return {
        "success": True,
        "message": "Imagem regenerada com sucesso",
        "path": str(image_path),
    }

