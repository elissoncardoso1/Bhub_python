"""
Serviço de geração de Open Graph dinâmico para artigos científicos.
"""

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from app.config import settings
from app.database import get_session_context
from app.models import Article


class OpenGraphService:
    """Serviço para geração de metadados e imagens Open Graph."""

    # Dimensões padrão para imagens OG
    OG_IMAGE_WIDTH = 1200
    OG_IMAGE_HEIGHT = 630

    # Cores do tema BHub (ajustar conforme necessário)
    COLORS = {
        "primary": "#0D9488",  # Teal
        "secondary": "#1E293B",  # Navy
        "background": "#FFFFFF",
        "text": "#1E293B",
        "text_light": "#64748B",
        "accent": "#F59E0B",  # Yellow
    }

    def __init__(self):
        """Inicializa o serviço."""
        self.cache_dir = settings.upload_dir / "og_images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_font_path(self, font_name: str = "arial.ttf") -> str | None:
        """Retorna caminho da fonte ou None para usar padrão."""
        # Tentar encontrar fontes comuns
        common_paths = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "/Windows/Fonts/arial.ttf",  # Windows
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Carrega fonte ou retorna padrão."""
        font_path = self._get_font_path()
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass

        # Fallback para fonte padrão
        return ImageFont.load_default()

    def _truncate_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> str:
        """Trunca texto para caber na largura especificada."""
        if not text:
            return ""

        # Medir texto
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        text_width = draw.textlength(text, font=font)

        if text_width <= max_width:
            return text

        # Truncar com ellipsis
        ellipsis = "..."
        ellipsis_width = draw.textlength(ellipsis, font=font)
        max_text_width = max_width - ellipsis_width

        while len(text) > 0:
            text = text[:-1]
            if draw.textlength(text, font=font) <= max_text_width:
                break

        return text + ellipsis

    def _wrap_text(
        self, text: str, max_width: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_lines: int = 3
    ) -> list[str]:
        """Quebra texto em múltiplas linhas."""
        if not text:
            return []

        words = text.split()
        lines = []
        current_line = ""

        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

        for word in words:
            test_line = f"{current_line} {word}".strip()
            width = draw.textlength(test_line, font=font)

            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    if len(lines) >= max_lines:
                        break
                current_line = word

        if current_line and len(lines) < max_lines:
            lines.append(current_line)

        return lines

    async def generate_article_image(self, article: Article) -> Path:
        """
        Gera imagem Open Graph para um artigo.

        Args:
            article: Artigo para gerar imagem

        Returns:
            Path do arquivo de imagem gerado
        """
        # Verificar cache
        cache_key = self._get_cache_key(article.id)
        cache_path = self.cache_dir / f"{cache_key}.png"

        # Se já existe e está atualizado, retornar
        if cache_path.exists():
            # Verificar se precisa regenerar (se artigo foi atualizado recentemente)
            article_updated = article.updated_at or article.created_at
            if article_updated and cache_path.stat().st_mtime >= article_updated.timestamp():
                return cache_path

        # Criar imagem
        img = Image.new("RGB", (self.OG_IMAGE_WIDTH, self.OG_IMAGE_HEIGHT), self.COLORS["background"])
        draw = ImageDraw.Draw(img)

        # Fontes
        title_font = self._load_font(48, bold=True)
        subtitle_font = self._load_font(28)
        meta_font = self._load_font(20)

        # Padding
        padding = 60
        content_width = self.OG_IMAGE_WIDTH - (padding * 2)

        # Título (truncado)
        title = article.title_translated or article.title
        title_lines = self._wrap_text(title, content_width, title_font, max_lines=2)
        title_y = padding

        for line in title_lines:
            draw.text((padding, title_y), line, fill=self.COLORS["text"], font=title_font)
            # Calcular altura da linha
            try:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                line_height = bbox[3] - bbox[1]
            except AttributeError:
                # Fallback para versões antigas do Pillow
                bbox = draw.textsize(line, font=title_font)
                line_height = bbox[1]
            title_y += line_height + 10

        # Separador
        separator_y = title_y + 30
        draw.line([(padding, separator_y), (self.OG_IMAGE_WIDTH - padding, separator_y)], fill=self.COLORS["text_light"], width=2)

        # Abstract (truncado)
        abstract_y = separator_y + 40
        if article.abstract_translated or article.abstract:
            abstract = (article.abstract_translated or article.abstract)[:200]  # Limitar tamanho
            abstract_lines = self._wrap_text(abstract, content_width, subtitle_font, max_lines=3)

            for line in abstract_lines:
                draw.text((padding, abstract_y), line, fill=self.COLORS["text_light"], font=subtitle_font)
                try:
                    bbox = draw.textbbox((0, 0), line, font=subtitle_font)
                    line_height = bbox[3] - bbox[1]
                except AttributeError:
                    # Fallback para versões antigas do Pillow
                    bbox = draw.textsize(line, font=subtitle_font)
                    line_height = bbox[1]
                abstract_y += line_height + 8

        # Metadata na parte inferior
        meta_y = self.OG_IMAGE_HEIGHT - 80

        # Categoria
        if article.category:
            category_text = article.category.name
            draw.text((padding, meta_y), category_text, fill=self.COLORS["primary"], font=meta_font)

        # Data de publicação
        if article.publication_date:
            date_text = article.publication_date.strftime("%d/%m/%Y")
            date_width = draw.textlength(date_text, font=meta_font)
            draw.text((self.OG_IMAGE_WIDTH - padding - date_width, meta_y), date_text, fill=self.COLORS["text_light"], font=meta_font)

        # Logo/Branding (opcional - adicionar se tiver logo)
        # brand_y = self.OG_IMAGE_HEIGHT - 50
        # draw.text((padding, brand_y), "BHub", fill=self.COLORS["primary"], font=meta_font)

        # Salvar imagem
        img.save(cache_path, "PNG", optimize=True)
        return cache_path

    def _get_cache_key(self, article_id: int) -> str:
        """Gera chave de cache para artigo."""
        return f"article_{article_id}"

    async def get_article_metadata(self, article_id: int, base_url: str) -> dict[str, Any]:
        """
        Retorna metadados Open Graph para um artigo.

        Args:
            article_id: ID do artigo
            base_url: URL base da aplicação (ex: https://bhub.com.br)

        Returns:
            Dicionário com metadados Open Graph
        """
        async with get_session_context() as db:
            from sqlalchemy.orm import selectinload

            result = await db.execute(
                select(Article)
                .where(Article.id == article_id, Article.is_published == True)
                .options(
                    selectinload(Article.category),
                    selectinload(Article.authors),
                )
            )
            article = result.scalar_one_or_none()

            if not article:
                return self._get_default_metadata(base_url)

            # Gerar imagem se necessário
            image_path = await self.generate_article_image(article)
            image_url = f"{base_url}/api/v1/og/articles/{article_id}/image"

            # Título e descrição
            title = article.title_translated or article.title
            description = (article.abstract_translated or article.abstract or "")[:200]

            # URL do artigo
            article_url = f"{base_url}/articles/{article_id}"

            # Metadados
            metadata = {
                "og:title": title,
                "og:description": description,
                "og:type": "article",
                "og:url": article_url,
                "og:image": image_url,
                "og:image:width": str(self.OG_IMAGE_WIDTH),
                "og:image:height": str(self.OG_IMAGE_HEIGHT),
                "og:image:type": "image/png",
                "og:site_name": "BHub",
                "article:published_time": article.publication_date.isoformat() if article.publication_date else None,
                "article:author": article.authors_str if article.authors else None,
                "article:section": article.category.name if article.category else None,
                # Twitter Card
                "twitter:card": "summary_large_image",
                "twitter:title": title,
                "twitter:description": description,
                "twitter:image": image_url,
                # Meta tags padrão
                "title": title,
                "description": description,
            }

            # Remover valores None
            return {k: v for k, v in metadata.items() if v is not None}

    def _get_default_metadata(self, base_url: str) -> dict[str, Any]:
        """Retorna metadados padrão quando artigo não encontrado."""
        default_image = f"{base_url}/api/v1/og/default/image"

        return {
            "og:title": "BHub - Repositório de Análise do Comportamento",
            "og:description": "Repositório científico dedicado à análise do comportamento",
            "og:type": "website",
            "og:url": base_url,
            "og:image": default_image,
            "og:site_name": "BHub",
            "twitter:card": "summary_large_image",
            "twitter:title": "BHub - Repositório de Análise do Comportamento",
            "twitter:description": "Repositório científico dedicado à análise do comportamento",
            "twitter:image": default_image,
            "title": "BHub - Repositório de Análise do Comportamento",
            "description": "Repositório científico dedicado à análise do comportamento",
        }

    async def generate_default_image(self) -> Path:
        """Gera imagem padrão Open Graph."""
        cache_path = self.cache_dir / "default.png"

        if cache_path.exists():
            return cache_path

        img = Image.new("RGB", (self.OG_IMAGE_WIDTH, self.OG_IMAGE_HEIGHT), self.COLORS["background"])
        draw = ImageDraw.Draw(img)

        title_font = self._load_font(64, bold=True)
        subtitle_font = self._load_font(32)

        # Título centralizado
        title = "BHub"
        try:
            bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = bbox[2] - bbox[0]
        except AttributeError:
            # Fallback para versões antigas do Pillow
            bbox = draw.textsize(title, font=title_font)
            title_width = bbox[0]
        title_x = (self.OG_IMAGE_WIDTH - title_width) // 2
        title_y = (self.OG_IMAGE_HEIGHT // 2) - 50

        draw.text((title_x, title_y), title, fill=self.COLORS["primary"], font=title_font)

        # Subtítulo
        subtitle = "Repositório de Análise do Comportamento"
        try:
            bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            subtitle_width = bbox[2] - bbox[0]
        except AttributeError:
            # Fallback para versões antigas do Pillow
            bbox = draw.textsize(subtitle, font=subtitle_font)
            subtitle_width = bbox[0]
        subtitle_x = (self.OG_IMAGE_WIDTH - subtitle_width) // 2
        subtitle_y = title_y + 80

        draw.text((subtitle_x, subtitle_y), subtitle, fill=self.COLORS["text_light"], font=subtitle_font)

        img.save(cache_path, "PNG", optimize=True)
        return cache_path

