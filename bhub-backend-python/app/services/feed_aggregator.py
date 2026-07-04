"""
Serviço de agregação de feeds RSS/Atom.
"""

import asyncio
import json
import time
from datetime import datetime

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.models import Article, Author, Feed, SourceType
from app.schemas.feed import FeedSyncAllResult, FeedSyncResult, FeedTestResult
from app.services.article_parser import ArticleParserService
from app.services.feed_fetcher import FeedFetcher, FetchResult, FetchStatus
from app.services.task_dispatcher import dispatch_classify_article, dispatch_download_pdf


class FeedAggregatorService:
    """Serviço para agregação de feeds RSS/Atom."""

    def __init__(self, db: AsyncSession, ai_manager=None):
        self.db = db
        self.ai_manager = ai_manager
        self.parser = ArticleParserService()
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )
        self.fetcher = FeedFetcher()

    async def close(self):
        """Fecha o cliente HTTP."""
        await self.http_client.aclose()
        await self.fetcher.close()

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

        fetch_result = await self._fetch_feed(feed)

        # URL morta: tentar redescobrir o feed a partir do site antes de desistir
        if fetch_result.status is FetchStatus.GONE:
            new_url = await self._try_rediscover(feed)
            if new_url:
                feed.feed_url = new_url
                feed.http_etag = None
                feed.http_last_modified = None
                fetch_result = await self._fetch_feed(feed)

        if fetch_result.status is FetchStatus.NOT_MODIFIED:
            feed.last_sync_at = datetime.utcnow()
            feed.last_successful_sync_at = datetime.utcnow()
            feed.error_count = 0
            feed.last_error = None
            feed.articles_last_sync = 0
            await self.db.commit()
            log.info(f"Feed {feed.name} não modificado (HTTP 304)")
            return FeedSyncResult(
                feed_id=feed.id,
                feed_name=feed.name,
                success=True,
                new_articles=0,
                duration_seconds=time.time() - start_time,
            )

        if fetch_result.status is not FetchStatus.OK:
            return await self._record_fetch_failure(feed, fetch_result, start_time)

        try:
            # Parse do feed
            parsed = feedparser.parse(fetch_result.text)

            if parsed.bozo and parsed.bozo_exception:
                log.warning(f"Feed malformado: {feed.name} - {parsed.bozo_exception}")

            # Processar cada item
            articles_to_classify = []
            articles_to_download_pdf = []
            for entry in parsed.entries:
                try:
                    created_article_id, article_data = await self._process_feed_entry(feed, entry)
                    if created_article_id:
                        new_articles += 1
                        articles_to_classify.append(created_article_id)

                        # Verificar se é open access e tem PDF URL para download
                        if article_data and article_data.get("is_open_access") and article_data.get("pdf_url"):
                            articles_to_download_pdf.append(
                                (created_article_id, article_data.get("pdf_url"))
                            )
                except Exception as e:
                    log.error(f"Erro ao processar entrada: {e}")
                    errors.append(str(e))

            # Persistir validadores de cache HTTP para conditional GET
            feed.http_etag = fetch_result.etag
            feed.http_last_modified = fetch_result.last_modified

            # Atualizar estatísticas do feed
            feed.last_sync_at = datetime.utcnow()
            feed.last_successful_sync_at = datetime.utcnow()
            feed.error_count = 0
            feed.last_error = None
            feed.articles_last_sync = new_articles
            feed.total_articles += new_articles

            await self.db.commit()
            from app.core.telemetry import record_feed_ingested

            record_feed_ingested(new_articles, feed.name)

            # Disparar tarefas de classificação em background após commit
            if articles_to_classify:
                for art_id in articles_to_classify:
                    job_id = await dispatch_classify_article(art_id)
                    log.debug(f"Classificação enfileirada: job={job_id} artigo={art_id}")
                log.info(f"Enfileiradas {len(articles_to_classify)} tarefas de classificação")

            # Disparar tarefas de download de PDF para artigos open access
            if articles_to_download_pdf:
                for art_id, pdf_url in articles_to_download_pdf:
                    job_id = await dispatch_download_pdf(art_id, pdf_url)
                    log.debug(f"Download de PDF enfileirado: job={job_id} artigo={art_id}")
                log.info(f"Enfileiradas {len(articles_to_download_pdf)} tarefas de download de PDF")

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
            from app.core.telemetry import record_feed_failed

            record_feed_failed(feed.name)

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

    async def _process_feed_entry(self, feed: Feed, entry: dict) -> tuple[int | None, dict | None]:
        """Processa uma entrada do feed e cria artigo se necessário. Retorna ID do artigo criado."""
        # Gerar ID externo
        external_id = self.parser.generate_external_id(entry, feed.id)

        # Verificar se já existe
        existing = await self.db.execute(
            select(Article).where(Article.external_id == external_id)
        )
        if existing.scalar_one_or_none():
            return None, None

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
            pdf_url=article_data.get("pdf_url"),
            category_id=None, # Será preenchido via background task
            classification_confidence=None,
            is_open_access=article_data.get("is_open_access", False),
        )

        self.db.add(article)
        await self.db.flush()

        # Processar autores
        author_names = article_data.get("authors", [])
        await self._process_authors(article, author_names)

        return article.id, article_data

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
        from sqlalchemy import insert

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

    def _parse_custom_headers(self, feed: Feed) -> dict[str, str] | None:
        """Desserializa custom_headers (JSON) do feed, se houver."""
        if not feed.custom_headers:
            return None
        try:
            headers = json.loads(feed.custom_headers)
            if isinstance(headers, dict):
                return {str(k): str(v) for k, v in headers.items()}
        except (ValueError, TypeError) as e:
            log.warning(f"custom_headers inválido no feed {feed.name}: {e}")
        return None

    async def _fetch_feed(self, feed: Feed) -> FetchResult:
        """Fetch resiliente usando os validadores de cache persistidos no feed."""
        return await self.fetcher.fetch(
            feed.feed_url,
            etag=feed.http_etag,
            last_modified=feed.http_last_modified,
            custom_headers=self._parse_custom_headers(feed),
        )

    async def _record_fetch_failure(
        self, feed: Feed, fetch_result: FetchResult, start_time: float
    ) -> FeedSyncResult:
        """Registra falha de fetch. Erros transitórios não incrementam error_count."""
        from app.core.telemetry import record_feed_failed

        record_feed_failed(feed.name)

        error_msg = fetch_result.error or fetch_result.status.value
        feed.last_sync_at = datetime.utcnow()
        feed.last_error = error_msg
        if fetch_result.status is not FetchStatus.TRANSIENT_ERROR:
            feed.error_count += 1

        await self.db.commit()
        log.warning(f"Falha ao sincronizar feed {feed.name}: {error_msg}")

        return FeedSyncResult(
            feed_id=feed.id,
            feed_name=feed.name,
            success=False,
            errors=[error_msg],
            duration_seconds=time.time() - start_time,
        )

    async def _try_rediscover(self, feed: Feed) -> str | None:
        """Redescobre a URL do feed e valida contra a unique constraint de feed_url."""
        new_url = await self._rediscover_feed_url(feed)
        if not new_url:
            return None

        dup = await self.db.execute(
            select(Feed).where(Feed.feed_url == new_url, Feed.id != feed.id)
        )
        if dup.scalar_one_or_none() is not None:
            log.warning(
                f"Feed {feed.name}: URL redescoberta {new_url} já pertence a outro feed"
            )
            return None

        log.info(f"Feed {feed.name}: URL redescoberta {feed.feed_url} -> {new_url}")
        return new_url

    async def _rediscover_feed_url(self, feed: Feed) -> str | None:
        """Procura feeds no website do periódico e valida o primeiro candidato útil."""
        if not feed.website_url:
            return None

        try:
            from trafilatura import feeds as trafilatura_feeds

            # find_feed_urls é síncrono e faz I/O de rede — rodar em thread
            candidates = await asyncio.to_thread(
                trafilatura_feeds.find_feed_urls, feed.website_url
            )
        except Exception as e:
            log.warning(f"Redescoberta de feed falhou para {feed.name}: {e}")
            return None

        for candidate in candidates or []:
            if candidate == feed.feed_url:
                continue
            try:
                result = await self.fetcher.fetch(candidate)
            except Exception as e:
                log.debug(f"Candidato {candidate} falhou: {e}")
                continue
            if result.status is FetchStatus.OK and result.text:
                parsed = feedparser.parse(result.text)
                if parsed.entries:
                    return candidate

        return None

    async def test_feed(self, feed_url: str) -> FeedTestResult:
        """Testa um feed sem salvar dados."""
        try:
            fetch_result = await self.fetcher.fetch(feed_url)
            if fetch_result.status is not FetchStatus.OK:
                return FeedTestResult(
                    success=False,
                    error=fetch_result.error or fetch_result.status.value,
                )

            parsed = feedparser.parse(fetch_result.text)

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
