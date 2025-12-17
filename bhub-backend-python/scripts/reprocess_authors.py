"""
Script para reprocessar artigos existentes e extrair/associar autores.
"""

import asyncio
import sys
sys.path.insert(0, ".")

import feedparser
import httpx
from sqlalchemy import select, insert

from app.core.logging import setup_logging, log
from app.database import get_session_context, init_db
from app.models import Article, Author, Feed
from app.models.author import article_authors
from app.services.article_parser import ArticleParserService


async def reprocess_articles_authors():
    """Reprocessa artigos para extrair autores dos feeds originais."""
    setup_logging()
    log.info("=" * 60)
    log.info("Reprocessando autores dos artigos...")
    log.info("=" * 60)
    
    await init_db()
    parser = ArticleParserService()
    
    http_client = httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    
    async with get_session_context() as db:
        # Buscar todos os feeds ativos
        result = await db.execute(
            select(Feed).where(Feed.is_active == True)
        )
        feeds = result.scalars().all()
        
        total_articles_updated = 0
        total_authors_created = 0
        
        for feed in feeds:
            if feed.feed_url.startswith("internal://"):
                continue
                
            log.info(f"Processando feed: {feed.name}")
            
            try:
                response = await http_client.get(feed.feed_url)
                response.raise_for_status()
                parsed = feedparser.parse(response.text)
                
                for entry in parsed.entries:
                    # Extrair URL/ID único
                    entry_id = parser.generate_external_id(entry, feed.id)
                    
                    # Buscar artigo existente
                    result = await db.execute(
                        select(Article).where(Article.external_id == entry_id)
                    )
                    article = result.scalar_one_or_none()
                    
                    if not article:
                        continue
                    
                    # Verificar se já tem autores
                    check_assoc = await db.execute(
                        select(article_authors).where(
                            article_authors.c.article_id == article.id
                        )
                    )
                    if check_assoc.first():
                        continue
                    
                    # Extrair autores do entry
                    article_data = parser.parse_entry(entry)
                    author_names = article_data.get("authors", [])
                    
                    if not author_names:
                        continue
                    
                    log.info(f"  Artigo: {article.title[:50]}... -> Autores: {author_names}")
                    
                    for position, author_info in enumerate(author_names):
                        name = author_info.get("name")
                        role = author_info.get("role", "author")
                        
                        if not name or len(name.strip()) < 2:
                            continue
                        
                        normalized = Author.normalize_name(name)
                        if not normalized:
                            continue
                        
                        # Buscar ou criar autor
                        result = await db.execute(
                            select(Author).where(Author.normalized_name == normalized)
                        )
                        author = result.scalar_one_or_none()
                        
                        if not author:
                            author = Author(
                                name=name.strip(),
                                normalized_name=normalized,
                            )
                            db.add(author)
                            await db.flush()
                            total_authors_created += 1
                        
                        # Criar associação
                        check_stmt = select(article_authors).where(
                            article_authors.c.article_id == article.id,
                            article_authors.c.author_id == author.id
                        )
                        existing = await db.execute(check_stmt)
                        if existing.first() is None:
                            stmt = insert(article_authors).values(
                                article_id=article.id,
                                author_id=author.id,
                                position=position,
                                role=role
                            )
                            await db.execute(stmt)
                            author.article_count += 1
                    
                    total_articles_updated += 1
                    
            except Exception as e:
                log.error(f"Erro ao processar feed {feed.name}: {e}")
                continue
        
        await db.commit()
        
        log.info("")
        log.info("=" * 60)
        log.info("RESUMO DO REPROCESSAMENTO")
        log.info("=" * 60)
        log.info(f"  Artigos atualizados: {total_articles_updated}")
        log.info(f"  Autores criados: {total_authors_created}")
        log.info("=" * 60)
    
    await http_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(reprocess_articles_authors())
    except Exception as e:
        log.error(f"Erro ao executar reprocessamento: {e}", exc_info=True)
        sys.exit(1)
