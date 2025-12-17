"""
Serviço de agregação de feeds RSS/Atom.
"""

import asyncio
import time
from datetime import datetime

from app.services.background_tasks import classify_article_task
import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import log
from app.models import Article, Author, Feed, FeedType, SourceType
from app.schemas.feed import FeedSyncAllResult, FeedSyncResult, FeedTestResult
from app.services.article_parser import ArticleParserService


class FeedAggregatorService:
    """Serviço para agregação de feeds RSS/Atom."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = ArticleParserService()
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )

    async def close(self):
        """Fecha o cliente HTTP."""
        await self.http_client.aclose()

    async def sync_all_active_feeds(self) -> FeedSyncAllResult:
        """Sincroniza todos os feeds ativos."""
        start_time = time.time()
        log.bind(feed_sync=True).info("Iniciando sincronização de todos os feeds")

        # Buscar feeds ativos que precisam sincronização
        result = await self.db.execute(
            select(Feed).where(
                Feed.is_active == True,
                ~Feed.feed_url.startswith("internal://"),
            )
        )
        feeds = result.scalars().all()

        feeds_to_sync = [f for f in feeds if f.needs_sync]

        results: list[FeedSyncResult] = []
        total_new_articles = 0
        successful = 0
        failed = 0

        for feed in feeds_to_sync:
            try:
                sync_result = await self.sync_feed(feed.id)
                results.append(sync_result)
                total_new_articles += sync_result.new_articles
                if sync_result.success:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                log.error(f"Erro ao sincronizar feed {feed.name}: {e}")
                results.append(
                    FeedSyncResult(
                        feed_id=feed.id,
                        feed_name=feed.name,
                        success=False,
                        errors=[str(e)],
                    )
                )
                failed += 1

        duration = time.time() - start_time
        log.bind(feed_sync=True).info(
            f"Sincronização concluída: {successful} sucesso, {failed} falhas, "
            f"{total_new_articles} novos artigos em {duration:.2f}s"
        )

        return FeedSyncAllResult(
            total_feeds=len(feeds_to_sync),
            successful=successful,
            failed=failed,
            new_articles=total_new_articles,
            results=results,
            duration_seconds=duration,
        )

    async def sync_feed(self, feed_id: int) -> FeedSyncResult:
        """Sincroniza um feed específico."""
        start_time = time.time()

        # Buscar feed
        result = await self.db.execute(select(Feed).where(Feed.id == feed_id))
        feed = result.scalar_one_or_none()

        if not feed:
            return FeedSyncResult(
                feed_id=feed_id,
                feed_name="Unknown",
                success=False,
                errors=["Feed não encontrado"],
            )

        log.info(f"Sincronizando feed: {feed.name}")
        errors: list[str] = []
        new_articles = 0

        try:
            # Fazer requisição HTTP
            response = await self.http_client.get(feed.feed_url)
            response.raise_for_status()

            # Parse do feed
            parsed = feedparser.parse(response.text)

            if parsed.bozo and parsed.bozo_exception:
                log.warning(f"Feed malformado: {feed.name} - {parsed.bozo_exception}")

            # Processar cada item
            articles_to_classify = []
            for entry in parsed.entries:
                try:
                    created_article_id = await self._process_feed_entry(feed, entry)
                    if created_article_id:
                        new_articles += 1
                        articles_to_classify.append(created_article_id)
                except Exception as e:
                    log.error(f"Erro ao processar entrada: {e}")
                    errors.append(str(e))

            # Atualizar estatísticas do feed
            feed.last_sync_at = datetime.utcnow()
            feed.last_successful_sync_at = datetime.utcnow()
            feed.error_count = 0
            feed.last_error = None
            feed.articles_last_sync = new_articles
            feed.total_articles += new_articles

            await self.db.commit()

            # Disparar tarefas de classificação em background após commit
            if articles_to_classify:
                for art_id in articles_to_classify:
                    asyncio.create_task(classify_article_task(art_id))
                log.info(f"Disparadas {len(articles_to_classify)} tarefas de classificação em background")

            duration = time.time() - start_time
            log.info(f"Feed {feed.name} sincronizado: {new_articles} novos artigos em {duration:.2f}s")

            return FeedSyncResult(
                feed_id=feed.id,
                feed_name=feed.name,
                success=True,
                new_articles=new_articles,
                errors=errors,
                duration_seconds=duration,
            )

        except Exception as e:
            log.error(f"Erro ao sincronizar feed {feed.name}: {e}")

            # Atualizar contagem de erros
            feed.last_sync_at = datetime.utcnow()
            feed.error_count += 1
            feed.last_error = str(e)

            await self.db.commit()

            return FeedSyncResult(
                feed_id=feed.id,
                feed_name=feed.name,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time,
            )

    async def _process_feed_entry(self, feed: Feed, entry: dict) -> int | None:
        """Processa uma entrada do feed e cria artigo se necessário. Retorna ID do artigo criado."""
        # Gerar ID externo
        external_id = self.parser.generate_external_id(entry, feed.id)

        # Verificar se já existe
        existing = await self.db.execute(
            select(Article).where(Article.external_id == external_id)
        )
        if existing.scalar_one_or_none():
            return None

        # Parse dos dados do artigo
        article_data = self.parser.parse_entry(entry, journal_name=feed.journal_name)
        
        # Fallback de autor: se não vier no feed, tentar buscar na página (específico para Springer/BAP)
        if not article_data.get("authors") and article_data.get("url"):
            domain = ""
            try:
                from urllib.parse import urlparse
                domain = urlparse(article_data["url"]).netloc
            except:
                pass
                
            # Adicionar domínios que sabemos que precisam disso
            if "springer.com" in domain or "wiley.com" in domain:
                try:
                    log.info(f"Buscando autores via scraping para: {article_data['url']}")
                    # Usar headers de navegador para evitar bloqueio
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
                    }
                    page_response = await self.http_client.get(article_data["url"], headers=headers, follow_redirects=True)
                    if page_response.status_code == 200:
                        scraped_authors = self.parser.parse_html_authors(page_response.text)
                        if scraped_authors:
                            article_data["authors"] = scraped_authors
                            log.info(f"Autores encontrados via scraping: {len(scraped_authors)}")
                except Exception as e:
                    log.warning(f"Falha no fallback de scraping de autores: {e}")

        # Classificação movida para background_tasks

        # Criar artigo
        article = Article(
            external_id=external_id,
            title=article_data["title"],
            abstract=article_data.get("abstract"),
            keywords=article_data.get("keywords"),
            original_url=article_data.get("url"),
            publication_date=article_data.get("publication_date"),
            doi=article_data.get("doi"),
            journal_name=feed.journal_name or article_data.get("journal"),
            language=article_data.get("language", "en"),
            source_type=SourceType.RSS,
            feed_id=feed.id,
            image_url=article_data.get("image_url"),
            category_id=None, # Será preenchido via background task
            classification_confidence=None,
        )

        self.db.add(article)
        await self.db.flush()

        # Processar autores
        author_names = article_data.get("authors", [])
        await self._process_authors(article, author_names)

        return article.id

    async def _process_authors(self, article: Article, author_names: list[dict]):
        """Processa e associa autores ao artigo."""
        if not author_names:
            return
            
        # Obter autores existentes
        existing_authors = {}
        if author_names: # author_names is now a list of dicts [{'name': '...', 'role': '...'}]
            names_to_check = [a['name'] for a in author_names if a and a.get('name')]
            if names_to_check:
                normalized_names = [Author.normalize_name(n) for n in names_to_check if Author.normalize_name(n)]
                if normalized_names:
                    stmt = select(Author).where(Author.normalized_name.in_(normalized_names))
                    result = await self.db.execute(stmt)
                    existing_authors = {a.normalized_name: a for a in result.scalars().all()}

        # Importar dinamicamente para evitar circular imports se necessário, ou usar o já importado
        from sqlalchemy import text, insert
        from app.models.author import article_authors 

        for idx, author_info in enumerate(author_names):
            name = author_info.get('name')
            role = author_info.get('role', 'author')
            
            if not name or len(name.strip()) < 2:
                continue

            norm_name = Author.normalize_name(name)
            
            if not norm_name:
                continue
            
            author = existing_authors.get(norm_name)
            if not author:
                # Double check in DB to avoid dupes from other concurrent tasks (rare but possible)
                # or from same batch if logic above failed
                stmt = select(Author).where(Author.normalized_name == norm_name)
                result = await self.db.execute(stmt)
                author = result.scalar_one_or_none()
                
                if author:
                    existing_authors[norm_name] = author
                else:
                    author = Author(name=name.strip(), normalized_name=norm_name)
                    self.db.add(author)
                    await self.db.flush() # Ensure ID is generated
                    existing_authors[norm_name] = author
            
            check_stmt = select(article_authors).where(
                article_authors.c.article_id == article.id,
                article_authors.c.author_id == author.id
            )
            existing_assoc = await self.db.execute(check_stmt)
            if existing_assoc.first() is None:
                # Inserir associação com role
                stmt = insert(article_authors).values(
                    article_id=article.id,
                    author_id=author.id,
                    position=idx,
                    role=role
                )
                await self.db.execute(stmt)
                author.article_count += 1

    async def test_feed(self, feed_url: str) -> FeedTestResult:
        """Testa um feed sem salvar dados."""
        try:
            response = await self.http_client.get(feed_url)
            response.raise_for_status()

            parsed = feedparser.parse(response.text)

            if not parsed.entries:
                return FeedTestResult(
                    success=False,
                    error="Feed não contém entradas",
                )

            # Pegar amostras
            sample_items = []
            for entry in parsed.entries[:3]:
                data = self.parser.parse_entry(entry)
                sample_items.append({
                    "title": data.get("title", "")[:100],
                    "url": data.get("url", ""),
                    "date": str(data.get("publication_date", "")),
                })

            return FeedTestResult(
                success=True,
                feed_title=parsed.feed.get("title"),
                feed_description=parsed.feed.get("description"),
                items_count=len(parsed.entries),
                sample_items=sample_items,
            )

        except httpx.HTTPError as e:
            return FeedTestResult(
                success=False,
                error=f"Erro HTTP: {e}",
            )
        except Exception as e:
            return FeedTestResult(
                success=False,
                error=str(e),
            )
