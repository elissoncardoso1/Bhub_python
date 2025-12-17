"""
Serviço de busca full-text com SQLite FTS5.
"""

import re
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models import Article, Category


class SearchService:
    """Serviço de busca full-text."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_fts5(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[int]:
        """
        Busca artigos usando FTS5.
        
        Returns:
            Lista de IDs de artigos ordenados por relevância
        """
        # Sanitizar query
        sanitized = self._sanitize_query(query)

        if not sanitized:
            return []

        try:
            result = await self.db.execute(
                text("""
                    SELECT rowid
                    FROM articles_fts
                    WHERE articles_fts MATCH :query
                    ORDER BY bm25(articles_fts)
                    LIMIT :limit OFFSET :offset
                """),
                {"query": sanitized, "limit": limit, "offset": offset},
            )

            return [row[0] for row in result.fetchall()]

        except Exception as e:
            log.warning(f"FTS5 search failed: {e}")
            return []

    async def search_with_ranking(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: int | None = None,
        boost_recent: bool = True,
        boost_impact: bool = True,
    ) -> list[tuple[int, float]]:
        """
        Busca com ranking customizado.
        
        Returns:
            Lista de tuplas (article_id, score)
        """
        sanitized = self._sanitize_query(query)

        if not sanitized:
            return []

        try:
            # Query base com FTS5 e boosts
            sql = """
                WITH fts_results AS (
                    SELECT 
                        rowid,
                        bm25(articles_fts, 2.0, 1.0, 0.5) as base_score
                    FROM articles_fts
                    WHERE articles_fts MATCH :query
                )
                SELECT 
                    f.rowid,
                    f.base_score 
                    + CASE WHEN a.highlighted = 1 THEN 5.0 ELSE 0 END
                    + CASE WHEN :boost_recent AND a.publication_date > :recent_date 
                           THEN 2.0 ELSE 0 END
                    + CASE WHEN :boost_impact THEN (a.impact_score - 5) * 0.3 ELSE 0 END
                    as final_score
                FROM fts_results f
                JOIN articles a ON f.rowid = a.id
                WHERE a.is_published = 1
            """

            params = {
                "query": sanitized,
                "boost_recent": boost_recent,
                "boost_impact": boost_impact,
                "recent_date": datetime.utcnow() - timedelta(days=30),
            }

            if category_id:
                sql += " AND a.category_id = :category_id"
                params["category_id"] = category_id

            sql += " ORDER BY final_score DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = await self.db.execute(text(sql), params)

            return [(row[0], row[1]) for row in result.fetchall()]

        except Exception as e:
            log.warning(f"FTS5 ranked search failed: {e}")
            return []

    async def search_like_fallback(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: int | None = None,
    ) -> list[int]:
        """
        Busca fallback usando LIKE quando FTS5 não está disponível.
        """
        terms = query.split()

        stmt = select(Article.id).where(Article.is_published == True)

        # Adicionar condições de busca
        for term in terms:
            pattern = f"%{term}%"
            stmt = stmt.where(
                (Article.title.ilike(pattern))
                | (Article.abstract.ilike(pattern))
                | (Article.keywords.ilike(pattern))
            )

        if category_id:
            stmt = stmt.where(Article.category_id == category_id)

        stmt = (
            stmt.order_by(Article.highlighted.desc(), Article.publication_date.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def get_suggestions(
        self,
        query: str,
        limit: int = 10,
    ) -> list[str]:
        """
        Retorna sugestões de busca baseadas no query.
        """
        if len(query) < 2:
            return []

        pattern = f"%{query}%"

        # Buscar títulos que contêm o termo
        result = await self.db.execute(
            select(Article.title)
            .where(
                Article.is_published == True,
                Article.title.ilike(pattern),
            )
            .distinct()
            .limit(limit)
        )

        titles = [row[0] for row in result.fetchall()]

        # Extrair termos relevantes
        suggestions = set()
        for title in titles:
            words = title.split()
            for word in words:
                if query.lower() in word.lower() and len(word) > 3:
                    suggestions.add(word)

        # Adicionar categorias
        cat_result = await self.db.execute(
            select(Category.name).where(Category.name.ilike(pattern))
        )
        for row in cat_result.fetchall():
            suggestions.add(row[0])

        return list(suggestions)[:limit]

    def _sanitize_query(self, query: str) -> str:
        """
        Sanitiza query para uso com FTS5.
        Remove caracteres especiais e formata para match.
        """
        # Remover caracteres especiais do FTS5
        sanitized = re.sub(r'[*"\'():\-]', " ", query)

        # Remover espaços extras
        sanitized = " ".join(sanitized.split())

        if not sanitized:
            return ""

        # Converter para formato de busca
        terms = sanitized.split()

        # Se apenas um termo, usar prefix matching
        if len(terms) == 1:
            return f"{terms[0]}*"

        # Múltiplos termos: usar AND implícito
        return " ".join(f"{term}*" for term in terms)

    async def rebuild_fts_index(self):
        """Reconstrói o índice FTS5."""
        try:
            await self.db.execute(text("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')"))
            await self.db.commit()
            log.info("Índice FTS5 reconstruído com sucesso")
        except Exception as e:
            log.error(f"Erro ao reconstruir índice FTS5: {e}")
            raise

    async def get_search_stats(self) -> dict:
        """Retorna estatísticas de busca."""
        try:
            result = await self.db.execute(
                text("SELECT COUNT(*) FROM articles_fts")
            )
            indexed_count = result.scalar()

            return {
                "indexed_articles": indexed_count,
                "fts_available": True,
            }
        except Exception:
            return {
                "indexed_articles": 0,
                "fts_available": False,
            }
