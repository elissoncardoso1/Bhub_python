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
from app.models import Article, Author, Feed, FeedJournalSource, SourceType
from app.schemas.feed import FeedSyncAllResult, FeedSyncResult, FeedTestResult
from app.services.article_parser import ArticleParserService
from app.services.crossref_source import CrossrefSource
from app.services.feed_fetcher import FeedFetcher, FetchResult, FetchStatus
from app.services.task_dispatcher import dispatch_classify_article, dispatch_download_pdf

# Prefixo aceito por ``test_feed`` para validar um ISSN antes de cadastrá-lo:
# ``issn:1938-3703``. Evita que a curadoria precise saber de cor a URL do
# endpoint do Crossref, e reaproveita o teste de feed que já existe no admin.
CROSSREF_ISSN_SCHEME = "issn:"


def _truncate(value: str | None, max_length: int) -> str | None:
    """Trunca strings ao limite da coluna para evitar StringDataRightTruncationError.

    Feeds podem trazer URLs/títulos maiores que o tamanho das colunas
    (ex.: image_url do Blogger com alt-text codificado). Cortar aqui impede
    que uma única entrada inválida derrube o flush e aborte a sincronização.
    """
    if value is None:
        return None
    return value[:max_length]


class FeedAggregatorService:
    """Serviço para agregação de feeds RSS/Atom."""

    def __init__(
        self,
        db: AsyncSession,
        ai_manager=None,
        parser: ArticleParserService | None = None,
        fetcher: FeedFetcher | None = None,
        http_client: httpx.AsyncClient | None = None,
        crossref: CrossrefSource | None = None,
    ):
        self.db = db
        self.ai_manager = ai_manager
        self.parser = parser or ArticleParserService()
        # Client HTTP próprio (dono) quando não injetado; injetado pertence
        # ao chamador — ``close`` só fecha o que criou (paridade com FeedFetcher).
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )
        self.fetcher = fetcher or FeedFetcher()
        # Fonte alternativa para periódicos, usada quando o RSS da editora está
        # atrás de anti-bot (ADR-0007).
        self.crossref = crossref or CrossrefSource()

    async def close(self):
        """Fecha o cliente HTTP (apenas se de propriedade do serviço)."""
        if self._owns_http_client:
            await self.http_client.aclose()
        await self.fetcher.close()
        await self.crossref.close()

    async def sync_all_active_feeds(self) -> FeedSyncAllResult:
        """Sincroniza todos os feeds ativos."""
        start_time = time.time()
        log.bind(feed_sync=True).info("Iniciando sincronização de todos os feeds")

        # Buscar feeds que precisam de sincronização.
        #
        # O filtro NÃO é ``is_active`` sozinho: um feed desativado por excesso
        # de erro precisa continuar elegível à sonda de recuperação de
        # ``Feed.needs_sync`` (ADR-0007). Sem a segunda condição, desativar o
        # feed o excluía da consulta e a sonda semanal virava código morto —
        # exatamente o defeito D2 do incidente de 2026-09-22.
        result = await self.db.execute(
            select(Feed).where(
                (Feed.is_active) | (Feed.error_count >= Feed.max_errors),
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

        is_crossref = feed.journal_source is FeedJournalSource.CROSSREF

        if is_crossref:
            # Periódico atrás de anti-bot no RSS: buscar pelo ISSN no Crossref
            # (ADR-0007). Sem redescoberta nem conditional GET — o Crossref não
            # usa ETag e a URL é derivada do ISSN.
            fetch_result = await self.crossref.fetch_works(
                feed.issn,
                last_successful_sync_at=feed.last_successful_sync_at,
            )
        else:
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

        entries, failure = self._extract_entries(feed, fetch_result, is_crossref=is_crossref)
        if failure is not None:
            return await self._record_fetch_failure(feed, failure, start_time)

        try:
            articles_to_classify: list[int] = []
            articles_to_download_pdf: list[tuple[int, str]] = []

            for entry in entries:
                try:
                    # Savepoint por entrada: se o flush de uma entrada falhar, só ela
                    # é revertida — a transação do feed continua válida e as demais
                    # entradas (e o commit final) seguem normalmente.
                    async with self.db.begin_nested():
                        created_article_id, article_data = await self._process_feed_entry(
                            feed, entry
                        )
                    if created_article_id:
                        new_articles += 1
                        articles_to_classify.append(created_article_id)

                        # Verificar se é open access e tem PDF URL para download
                        pdf_url = article_data.get("pdf_url") if article_data else None
                        if article_data and article_data.get("is_open_access") and pdf_url:
                            articles_to_download_pdf.append((created_article_id, pdf_url))
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

            # Sonda de recuperação bem-sucedida devolve o feed à rotação. Só se
            # aplica a desativação automática: um feed desligado pela curadoria
            # tem `deactivated_by_errors=False` e permanece fora.
            if not feed.is_active and feed.deactivated_by_errors:
                feed.is_active = True
                feed.deactivated_by_errors = False
                log.warning(
                    f"Feed {feed.name} (id={feed.id}) reativado: a sonda de "
                    f"recuperação teve sucesso após a desativação por erros"
                )

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
            log.info(
                f"Feed {feed.name} sincronizado: {new_articles} novos artigos em {duration:.2f}s"
            )

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

            # Exceção inesperada no meio da ingestão é falha permanente do
            # ponto de vista do feed — o mesmo tratamento de _record_fetch_failure,
            # incluindo a desativação por max_errors (D2). Sem isso, um feed que
            # sempre estoura exceção jamais sairia da rotação.
            feed.last_sync_at = datetime.utcnow()
            feed.error_count += 1
            feed.last_error = str(e)

            if feed.is_active and feed.error_count >= feed.max_errors:
                feed.is_active = False
                feed.deactivated_by_errors = True
                log.warning(
                    f"Feed {feed.name} (id={feed.id}) desativado após "
                    f"{feed.error_count} falhas (max_errors={feed.max_errors})"
                )

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
        existing = await self.db.execute(select(Article).where(Article.external_id == external_id))
        if existing.scalar_one_or_none():
            return None, None

        # Parse dos dados do artigo
        article_data = self.parser.parse_entry(entry, journal_name=feed.journal_name)

        # Fallback de autor: se não vier no feed, tentar buscar na página (específico para Springer/BAP)
        #
        # Não se aplica ao Crossref: ali os autores já vêm no payload, e o
        # `original_url` aponta para doi.org -> editora, isto é, exatamente o
        # host que responde 403. Buscar a página reintroduziria o bloqueio que
        # o ADR-0007 tirou do caminho, agora gastando latência por artigo.
        if (
            feed.journal_source is not FeedJournalSource.CROSSREF
            and not article_data.get("authors")
            and article_data.get("url")
        ):
            domain = ""
            try:
                from urllib.parse import urlparse

                domain = urlparse(article_data["url"]).netloc
            except Exception:
                pass

            # Adicionar domínios que sabemos que precisam disso
            if "springer.com" in domain or "wiley.com" in domain:
                try:
                    log.info(f"Buscando autores via scraping para: {article_data['url']}")
                    # Usar headers de navegador para evitar bloqueio
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
                    }
                    page_response = await self.http_client.get(
                        article_data["url"], headers=headers, follow_redirects=True
                    )
                    if page_response.status_code == 200:
                        scraped_authors = self.parser.parse_html_authors(page_response.text)
                        if scraped_authors:
                            article_data["authors"] = scraped_authors
                            log.info(f"Autores encontrados via scraping: {len(scraped_authors)}")
                except Exception as e:
                    log.warning(f"Falha no fallback de scraping de autores: {e}")

        # Classificação movida para background_tasks

        # Criar artigo
        # Truncar campos VARCHAR ao limite da coluna (ver _truncate). Abstract/keywords
        # são TEXT e não precisam de corte.
        article = Article(
            external_id=_truncate(external_id, 255),
            title=_truncate(article_data["title"], 500),
            abstract=article_data.get("abstract"),
            keywords=article_data.get("keywords"),
            original_url=_truncate(article_data.get("url"), 500),
            publication_date=article_data.get("publication_date"),
            doi=_truncate(article_data.get("doi"), 100),
            journal_name=_truncate(feed.journal_name or article_data.get("journal"), 255),
            language=_truncate(article_data.get("language", "en"), 10),
            source_type=SourceType.RSS,
            feed_id=feed.id,
            image_url=_truncate(article_data.get("image_url"), 500),
            pdf_url=_truncate(article_data.get("pdf_url"), 500),
            category_id=None,  # Será preenchido via background task
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
        if author_names:  # author_names is now a list of dicts [{'name': '...', 'role': '...'}]
            names_to_check = [a["name"] for a in author_names if a and a.get("name")]
            if names_to_check:
                normalized_names = [
                    Author.normalize_name(n) for n in names_to_check if Author.normalize_name(n)
                ]
                if normalized_names:
                    stmt = select(Author).where(Author.normalized_name.in_(normalized_names))
                    result = await self.db.execute(stmt)
                    existing_authors = {a.normalized_name: a for a in result.scalars().all()}

        # Importar dinamicamente para evitar circular imports se necessário, ou usar o já importado
        from sqlalchemy import insert

        from app.models.author import article_authors

        for idx, author_info in enumerate(author_names):
            name = author_info.get("name")
            role = author_info.get("role", "author")

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
                    await self.db.flush()  # Ensure ID is generated
                    existing_authors[norm_name] = author

            check_stmt = select(article_authors).where(
                article_authors.c.article_id == article.id, article_authors.c.author_id == author.id
            )
            existing_assoc = await self.db.execute(check_stmt)
            if existing_assoc.first() is None:
                # Inserir associação com role
                stmt = insert(article_authors).values(
                    article_id=article.id, author_id=author.id, position=idx, role=role
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

    def _extract_entries(
        self, feed: Feed, fetch_result: FetchResult, *, is_crossref: bool
    ) -> tuple[list[dict], FetchResult | None]:
        """Normaliza a resposta da fonte em uma lista de entradas para ingestão.

        Duas origens, um mesmo formato de saída: o Crossref já entrega entradas
        no formato do feedparser (``CrossrefSource``), o RSS é parseado aqui.
        Retorna ``(entradas, None)`` em sucesso ou ``( [], falha )`` quando o
        corpo não é um feed — caso que o chamador encaminha a
        ``_record_fetch_failure``.
        """
        if is_crossref:
            try:
                payload = json.loads(fetch_result.text or "")
                entries = payload.get("entries") or []
            except (ValueError, TypeError) as e:
                return [], FetchResult(
                    status=FetchStatus.INVALID_CONTENT,
                    error=f"Resposta do Crossref ilegível: {e}",
                )
            return entries, None

        parsed = feedparser.parse(fetch_result.text)

        # HTTP 200 não basta para declarar sucesso: endpoints de feed atrás de
        # anti-bot (ex.: o "Client Challenge" da Fastly na Springer) respondem
        # 200 com HTML. O feedparser só preenche `version` quando reconhece um
        # RSS/Atom, então corpo não-feed (HTML, vazio, JSON) deixa `version`
        # vazia — sem depender do Content-Type, que alguns servidores erram.
        # Um feed VÁLIDO com 0 itens mantém `version` e segue sendo sucesso.
        # `bozo` de propósito NÃO é critério: ele sinaliza "o parse teve avisos",
        # e um RSS válido com problema menor vem bozo=True com version='rss20'.
        # `.get`: com corpo vazio o feedparser nem cria a chave `version`, e o
        # acesso por atributo levantaria AttributeError.
        if not parsed.get("version"):
            log.warning(
                f"Feed {feed.name} (id={feed.id}) respondeu 200 com conteúdo "
                f"que não é RSS/Atom: {feed.feed_url}"
            )
            return [], FetchResult(
                status=FetchStatus.INVALID_CONTENT,
                error="Invalid feed response: conteúdo não é RSS/Atom",
            )

        if parsed.bozo and parsed.bozo_exception:
            log.warning(f"Feed malformado: {feed.name} - {parsed.bozo_exception}")

        return list(parsed.entries), None

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

            # Desativação por excesso de erro (defeito D2 do incidente de
            # 2026-09-22): até aqui o `max_errors` não surtia efeito nenhum, e
            # feeds com error_count=16 contra max_errors=5 continuavam na
            # rotação, gastando requisições inúteis contra hosts que já os
            # bloqueiam.
            #
            # Só falha **permanente** desativa. Um 502 ou timeout não justifica
            # tirar o feed da rotação: não é defeito da fonte, e a mensagem de
            # log ("desativado após N falhas") ficaria falsa.
            #
            # Isto NÃO é morte permanente: `Feed.needs_sync` mantém a sonda de
            # recuperação de 7 dias para feeds desativados por erro, e
            # `sync_all_active_feeds` os inclui na consulta por isso. Um sync
            # bem sucedido zera `error_count` — mas a reativação é decisão de
            # curadoria, porque o padrão de falha que desativou o feed é dado
            # útil.
            if feed.is_active and feed.error_count >= feed.max_errors:
                feed.is_active = False
                feed.deactivated_by_errors = True
                log.warning(
                    f"Feed {feed.name} (id={feed.id}) desativado após "
                    f"{feed.error_count} falhas (max_errors={feed.max_errors}): {error_msg}"
                )

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
            log.warning(f"Feed {feed.name}: URL redescoberta {new_url} já pertence a outro feed")
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
            candidates = await asyncio.to_thread(trafilatura_feeds.find_feed_urls, feed.website_url)
        except Exception as e:
            log.warning(f"Redescoberta de feed falhou para {feed.name}: {e}")
            return None

        # find_feed_urls pode devolver links de artigos quando não acha feed real;
        # a validação abaixo rejeita, mas limitamos o número de fetches
        for candidate in (candidates or [])[:5]:
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

    async def _test_crossref_feed(self, feed_url: str) -> FeedTestResult:
        """Valida um ISSN no Crossref e devolve uma amostra dos works recentes.

        Cadastrar um ISSN errado (dígito trocado, ISSN impresso em vez do
        eletrônico) produz um feed silenciosamente vazio — o modo de falha que
        o ADR-0006 combate. Aqui o erro aparece na hora do cadastro.
        """
        issn = feed_url[len(CROSSREF_ISSN_SCHEME) :].strip()

        exists, title_or_error = await self.crossref.validate_issn(issn)
        if not exists:
            return FeedTestResult(success=False, error=title_or_error)

        fetch_result = await self.crossref.fetch_works(issn, last_successful_sync_at=None)
        if fetch_result.status is not FetchStatus.OK:
            return FeedTestResult(
                success=False,
                feed_title=title_or_error,
                error=fetch_result.error or fetch_result.status.value,
            )

        entries, failure = self._extract_entries(
            feed=Feed(name=issn, feed_url=feed_url),
            fetch_result=fetch_result,
            is_crossref=True,
        )
        if failure is not None:
            return FeedTestResult(success=False, feed_title=title_or_error, error=failure.error)

        sample_items = []
        for entry in entries[:3]:
            data = self.parser.parse_entry(entry)
            sample_items.append(
                {
                    "title": (data.get("title") or "")[:100],
                    "url": data.get("url") or "",
                    "date": str(data.get("publication_date") or ""),
                }
            )

        return FeedTestResult(
            success=True,
            feed_title=title_or_error,
            feed_description=f"Crossref ISSN {issn}",
            items_count=len(entries),
            sample_items=sample_items,
        )

    async def test_feed(self, feed_url: str) -> FeedTestResult:
        """Testa um feed sem salvar dados."""
        if feed_url.startswith(CROSSREF_ISSN_SCHEME):
            return await self._test_crossref_feed(feed_url)

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
                sample_items.append(
                    {
                        "title": data.get("title", "")[:100],
                        "url": data.get("url", ""),
                        "date": str(data.get("publication_date", "")),
                    }
                )

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
