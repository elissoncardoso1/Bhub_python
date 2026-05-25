"""
Serviço de classificação de artigos com suporte a múltiplas categorias
e criação automática de categorias quando necessário.
"""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.interfaces.services import IAIManager
from app.models import Article, Category, article_categories
from app.models.category import DEFAULT_CATEGORIES


class ClassificationService:
    """Serviço para classificação de artigos com múltiplas categorias."""

    def __init__(self, db: AsyncSession, ai_manager: IAIManager | None = None):
        self.db = db
        self.ai_manager = ai_manager

    async def classify(self, text: str) -> tuple[str, float]:
        """Classifica texto com IA configurada e fallback local/heurístico."""
        if self.ai_manager:
            try:
                result = await self.ai_manager.classify(text)
                category_slug = result[0]
                confidence = result[1]
                if category_slug:
                    return category_slug, confidence
            except Exception as e:
                log.warning(f"Erro na classificação via AIManager: {e}")

        try:
            from app.ml import EmbeddingClassifier, HeuristicClassifier

            if EmbeddingClassifier.is_initialized():
                category_slug, confidence = await EmbeddingClassifier.classify(text)
                if category_slug != "outros" or confidence > 0:
                    return category_slug, confidence

            return HeuristicClassifier.classify(text)
        except Exception as e:
            log.warning(f"Fallback local de classificação falhou: {e}")
            return "outros", 0.0

    async def classify_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        """Classifica textos em lote preservando fallback por item."""
        return [await self.classify(text) for text in texts]

    async def classify_article(self, article_id: int) -> tuple[str, float] | None:
        """Classifica um artigo e persiste a categoria principal."""
        result = await self.db.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if not article:
            log.warning(f"Artigo {article_id} não encontrado para classificação")
            return None

        text_parts = [article.title]
        if article.abstract:
            text_parts.append(article.abstract)
        if article.keywords:
            text_parts.append(article.keywords)

        category_slug, confidence = await self.classify(" ".join(text_parts))
        assigned_categories = await self.assign_categories_to_article(
            db=self.db,
            article_id=article_id,
            category_slugs_with_confidence=[(category_slug, confidence)],
            auto_create=True,
        )

        if assigned_categories:
            article.classification_confidence = confidence
            await self.db.flush()

        return category_slug, confidence

    @staticmethod
    def normalize_slug(text: str) -> str:
        """Normaliza texto para criar slug."""
        # Remove acentos
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))

        # Lowercase e substitui espaços por hífens
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = normalized.strip("-")

        return normalized

    @staticmethod
    async def get_or_create_category(
        db,
        slug: str,
        name: str | None = None,
        description: str | None = None,
        auto_created: bool = True,
    ) -> Category:
        """
        Busca ou cria uma categoria.

        Args:
            db: Sessão do banco de dados
            slug: Slug da categoria
            name: Nome da categoria (se None, usa o slug capitalizado)
            description: Descrição da categoria
            auto_created: Se True, marca como criada automaticamente

        Returns:
            Category: Categoria encontrada ou criada
        """
        # Buscar categoria existente
        result = await db.execute(select(Category).where(Category.slug == slug))
        category = result.scalar_one_or_none()

        if category:
            return category

        # Criar nova categoria
        if not name:
            # Capitalizar primeira letra de cada palavra
            name = " ".join(word.capitalize() for word in slug.replace("-", " ").split())

        category = Category(
            name=name,
            slug=slug,
            description=description or f"Categoria criada automaticamente: {name}",
            color="#6B7280",  # Cor padrão cinza
            keywords="",  # Pode ser preenchido depois
        )

        db.add(category)
        await db.flush()

        log.info(f"Categoria criada automaticamente: {name} ({slug})")
        return category

    @staticmethod
    async def classify_with_multiple_categories(
        db,
        text: str,
        ai_manager,
        min_confidence: float = 0.3,
    ) -> list[tuple[str, float]]:
        """
        Classifica texto retornando múltiplas categorias com suas confianças.

        Args:
            db: Sessão do banco de dados
            text: Texto para classificar
            ai_manager: Instância do AIManager
            min_confidence: Confiança mínima para incluir categoria

        Returns:
            Lista de tuplas (category_slug, confidence)
        """
        # Primeiro, tentar classificação via AIManager (prioriza DeepSeek/APIs externas)
        try:
            category_slug, confidence, provider = await ai_manager.classify(text)
            if category_slug and confidence >= min_confidence:
                log.debug(f"Classificação via {provider}: {category_slug} ({confidence:.2f})")
                return [(category_slug, confidence)]
        except Exception as e:
            log.warning(f"Erro na classificação via AIManager: {e}")

        # Fallback: Tentar classificação múltipla com LLM local (se disponível)
        try:
            from app.ai.local_llm_service import LocalLLMService
            from app.ai.manager import AIProvider

            if AIProvider.LOCAL_LLM in ai_manager.providers:
                provider = ai_manager.providers[AIProvider.LOCAL_LLM]
                if isinstance(provider, LocalLLMService):
                    categories = await provider.classify_multiple(text)
                    if categories and categories != [("outros", 0.0)]:
                        log.debug(f"Classificação múltipla LLM local: {categories}")
                        return categories
        except Exception as e:
            log.debug(f"Classificação múltipla LLM local falhou: {e}")

        # Se não encontrou nenhuma categoria, retornar "outros" com baixa confiança
        return [("outros", 0.3)]

    @staticmethod
    async def assign_categories_to_article(
        db,
        article_id: int,
        category_slugs_with_confidence: list[tuple[str, float]],
        auto_create: bool = True,
    ) -> list[Category]:
        """
        Atribui múltiplas categorias a um artigo.

        Args:
            db: Sessão do banco de dados
            article_id: ID do artigo
            category_slugs_with_confidence: Lista de (slug, confidence)
            auto_create: Se True, cria categorias que não existem

        Returns:
            Lista de categorias atribuídas
        """
        assigned_categories = []

        # Ordenar por confiança (maior primeiro)
        category_slugs_with_confidence.sort(key=lambda x: x[1], reverse=True)

        for idx, (slug, confidence) in enumerate(category_slugs_with_confidence):
            # Buscar ou criar categoria
            if auto_create:
                category = await ClassificationService.get_or_create_category(
                    db, slug, auto_created=True
                )
            else:
                result = await db.execute(select(Category).where(Category.slug == slug))
                category = result.scalar_one_or_none()
                if not category:
                    log.warning(f"Categoria '{slug}' não encontrada e auto_create=False")
                    continue

            # Verificar se já existe associação
            check_stmt = select(article_categories).where(
                article_categories.c.article_id == article_id,
                article_categories.c.category_id == category.id,
            )
            existing = await db.execute(check_stmt)
            if existing.first():
                continue  # Já existe, pular

            # Criar associação
            is_primary = idx == 0  # Primeira categoria é primária

            # Verificar se categoria foi criada automaticamente (não está nas categorias padrão)
            default_category_names = [cat["name"] for cat in DEFAULT_CATEGORIES]
            auto_created_flag = category.name not in default_category_names

            stmt = insert(article_categories).values(
                article_id=article_id,
                category_id=category.id,
                confidence=confidence,
                is_primary=is_primary,
                auto_created=auto_created_flag,
            )
            await db.execute(stmt)

            assigned_categories.append(category)

            # Atualizar category_id primário se for a primeira
            if is_primary:
                from app.models import Article
                article_result = await db.execute(
                    select(Article).where(Article.id == article_id)
                )
                article = article_result.scalar_one_or_none()
                if article:
                    article.category_id = category.id
                    await db.flush()

        return assigned_categories
