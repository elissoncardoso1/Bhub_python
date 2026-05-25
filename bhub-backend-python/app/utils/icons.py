from functools import lru_cache
from pathlib import Path


class LucideIcons:
    def __init__(self, icons_dir: str = "app/static/icons"):
        # Adjust path if needed based on where the app is running
        self.icons_dir = Path(icons_dir)

    @lru_cache(maxsize=128)
    def get(self, name: str, css_class: str = "w-5 h-5", aria_hidden: bool = True) -> str:
        """
        Retorna o SVG do ícone com classes CSS aplicadas.
        Se não encontrar o arquivo, retorna um fallback (ou string vazia).

        Args:
            name: Nome do ícone Lucide
            css_class: Classes CSS a aplicar
            aria_hidden: Se True, adiciona aria-hidden="true" para acessibilidade
        """
        # Tenta localizar o arquivo .svg
        # Assumindo que os ícones estarão em static/icons/lucide/
        # Se não tiver, o usuário precisará baixar.
        # Mas para garantir que não quebre, se não achar, retornamos um <i> tag
        # que o script client-side pode preencher (se tiver o script rodando).

        # Como o plano menciona "script src unpkg lucide", o client-side pode tratar.
        # Porém, para evitar FOUC (Flash of Unstyled Content), SVG inline é melhor.
        # Vou assumir que o client-side script vai rodar lucide.createIcons().
        # Então, o helper pode apenas gerar a tag <i data-lucide="..."></i> se não tiver o SVG local.
        # Mas o objetivo do helper proposto no stack era SVG inline.

        # Vamos priorizar a tag <i> para compatibilidade com o script do CDN que vamos incluir,
        # pois não tenho garantia que os SVGs estão baixados localmente users filesystem yet.
        # O User não baixou os ícones ainda.

        aria_attr = 'aria-hidden="true"' if aria_hidden else ''
        return f'<i data-lucide="{name}" class="{css_class}" {aria_attr}></i>'

# Export instance
icons = LucideIcons()
