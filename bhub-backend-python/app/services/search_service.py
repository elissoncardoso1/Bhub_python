"""
Serviço de busca full-text com SQLite FTS5.
"""

import re
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models import Article, Category
from app.schemas.article import ArticleResponse


class SearchService:
    """Serviço de busca full-text."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _is_postgres(self) -> bool:
        bind = self.db.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"

    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ArticleResponse]:
        """Busca artigos e retorna schemas prontos para a API."""
        if self._is_postgres():
            article_ids = await self._search_postgres_ids(query, limit=limit, offset=offset)
        else:
            article_ids = await self.search_fts5(query, limit=limit, offset=offset)
            if not article_ids:
                article_ids = await self.search_like_fallback(query, limit=limit, offset=offset)

        if not article_ids:
            return []

        result = await self.db.execute(select(Article).where(Article.id.in_(article_ids)))
        articles_by_id = {article.id: article for article in result.scalars().all()}
        return [
            ArticleResponse.model_validate(articles_by_id[article_id])
            for article_id in article_ids
            if article_id in articles_by_id
        ]

    async def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        """Alias estável para sugestões via Protocol."""
        return await self.get_suggestions(prefix, limit=limit)

    async def _search_postgres_ids(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: int | None = None,
    ) -> list[int]:
        sanitized = self._sanitize_plain_query(query)
        if not sanitized:
            return []

        ts_query = func.plainto_tsquery("portuguese", sanitized)
        rank = func.ts_rank_cd(Article.search_vector, ts_query)

        stmt = (
            select(Article.id)
            .where(
                Article.is_published == True,
                Article.search_vector.op("@@")(ts_query),
            )
            .order_by(rank.desc(), Article.publication_date.desc())
            .limit(limit)
            .offset(offset)
        )
        if category_id:
            stmt = stmt.where(Article.category_id == category_id)

        result = await self.db.execute(stmt)
        return list(result.scalars())

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
        if self._is_postgres():
            return await self._search_postgres_ids(query, limit=limit, offset=offset)

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
        if self._is_postgres():
            ids = await self._search_postgres_ids(
                query,
                limit=limit,
                offset=offset,
                category_id=category_id,
            )
            return [(article_id, float(len(ids) - index)) for index, article_id in enumerate(ids)]

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

        if self._is_postgres():
            result = await self.db.execute(
                select(Article.title)
                .where(
                    Article.is_published == True,
                    Article.title.ilike(pattern),
                )
                .distinct()
                .order_by(func.similarity(Article.title, query).desc())
                .limit(limit)
            )
            return [row[0] for row in result.fetchall()]

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
        Sanitiza query para uso com FTS5 de forma segura.
        Previne SQL injection e manipulação do índice FTS5.
        """
        # Limitar tamanho máximo
        if len(query) > 200:
            query = query[:200]

        # Whitelist approach: apenas permitir caracteres alfanuméricos, espaços e acentos
        # Remover todos os caracteres especiais perigosos
        sanitized = re.sub(r'[^a-zA-Z0-9\s\u00C0-\u017F]', '', query)

        # Remover espaços extras
        sanitized = " ".join(sanitized.split())

        if not sanitized:
            return ""

        # Remover palavras reservadas do FTS5 que podem ser exploradas
        fts5_reserved = ['AND', 'OR', 'NOT', 'MATCH', 'NEAR', 'rebuild', 'DELETE']
        terms = sanitized.split()

        # Filtrar termos reservados e validar cada termo
        safe_terms = []
        for term in terms[:10]:  # Limitar número de termos
            term_upper = term.upper()
            # Pular palavras reservadas
            if term_upper in fts5_reserved:
                continue

            # Remover qualquer caractere especial restante
            clean_term = re.sub(r'[^a-zA-Z0-9\u00C0-\u017F]', '', term)

            # Validar tamanho mínimo e máximo
            if len(clean_term) >= 2 and len(clean_term) <= 50:
                safe_terms.append(clean_term)

        if not safe_terms:
            return ""

        # Usar escape do FTS5 com aspas para prevenir injeção
        # FTS5 trata strings entre aspas como literais
        escaped_terms = []
        for term in safe_terms:
            # Escapar aspas duplas dentro do termo
            escaped_term = term.replace('"', '""')
            # Usar aspas para tornar literal e adicionar wildcard
            escaped_terms.append(f'"{escaped_term}"*')

        # Retornar termos unidos com espaço (AND implícito no FTS5)
        return " ".join(escaped_terms)

    def _sanitize_plain_query(self, query: str) -> str:
        """Sanitiza query para plainto_tsquery/similaridade no PostgreSQL."""
        if len(query) > 200:
            query = query[:200]
        sanitized = re.sub(r"[^a-zA-Z0-9\s\u00C0-\u017F]", " ", query)
        return " ".join(sanitized.split()[:10])

    async def rebuild_fts_index(self):
        """Reconstrói o índice FTS5."""
        if self._is_postgres():
            await self.db.execute(
                text("""
                    UPDATE articles
                    SET search_vector =
                        setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
                        setweight(to_tsvector('portuguese', coalesce(abstract, '')), 'B') ||
                        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(abstract, '')), 'B')
                """)
            )
            await self.db.commit()
            log.info("Índice PostgreSQL TSVector reconstruído com sucesso")
            return

        try:
            await self.db.execute(text("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')"))
            await self.db.commit()
            log.info("Índice FTS5 reconstruído com sucesso")
        except Exception as e:
            log.error(f"Erro ao reconstruir índice FTS5: {e}")
            raise

    async def get_search_stats(self) -> dict:
        """Retorna estatísticas de busca."""
        if self._is_postgres():
            try:
                indexed_count = await self.db.scalar(
                    select(func.count()).select_from(Article).where(Article.search_vector.isnot(None))
                )
                return {
                    "indexed_articles": indexed_count or 0,
                    "fts_available": True,
                    "engine": "postgresql_tsvector",
                }
            except Exception:
                return {
                    "indexed_articles": 0,
                    "fts_available": False,
                    "engine": "postgresql_tsvector",
                }

        try:
            result = await self.db.execute(
                text("SELECT COUNT(*) FROM articles_fts")
            )
            indexed_count = result.scalar()

            return {
                "indexed_articles": indexed_count,
                "fts_available": True,
                "engine": "sqlite_fts5",
            }
        except Exception:
            return {
                "indexed_articles": 0,
                "fts_available": False,
                "engine": "sqlite_fts5",
            }
