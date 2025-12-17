"""
Script para popular feeds RSS no banco de dados.
Lê o arquivo FEEDS_RSS.md e cria os feeds organizados por categoria.
"""

import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from app.config import settings
from app.database import get_session_context, init_db
from app.models.feed import Feed, FeedType, SyncFrequency
from app.core.logging import log, setup_logging


# Feeds organizados por categoria e tipo
FEEDS_DATA = {
    "ABA Internacional": {
        "description": "Feeds RSS de fontes internacionais sobre Análise do Comportamento Aplicada",
        "feeds": [
            {
                "name": "ABAI Science Blog",
                "feed_url": "https://science.abainternational.org/feed/",
                "website_url": "https://science.abainternational.org",
                "description": "Blog científico da Association for Behavior Analysis International",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "I Love ABA!",
                "feed_url": "https://www.iloveaba.com/feeds/posts/default?alt=rss",
                "website_url": "https://www.iloveaba.com",
                "description": "Blog educacional sobre ABA e autismo",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Applied Behavior Analysis Edu",
                "feed_url": "https://www.appliedbehavioranalysisedu.org/feed/",
                "website_url": "https://www.appliedbehavioranalysisedu.org",
                "description": "Portal educacional sobre ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Verbal Beginnings Blog",
                "feed_url": "https://www.verbalbeginnings.com/feed/",
                "website_url": "https://www.verbalbeginnings.com",
                "description": "Blog sobre ABA e desenvolvimento de comunicação",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "ABA Works Blog",
                "feed_url": "https://aba-works.com/feed/",
                "website_url": "https://aba-works.com",
                "description": "Blog sobre práticas em ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Carolina Center for ABA",
                "feed_url": "https://carolinacenterforaba.com/feed/",
                "website_url": "https://carolinacenterforaba.com",
                "description": "Centro de ABA da Carolina do Norte",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "IABA Consultants Blog",
                "feed_url": "https://www.iabaconsultants.com/feed/",
                "website_url": "https://www.iabaconsultants.com",
                "description": "Blog de consultores em ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "All Day ABA",
                "feed_url": "https://alldayaba.org/blog/f.rss",
                "website_url": "https://alldayaba.org",
                "description": "Recursos e artigos sobre ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "ABA Speech Blog",
                "feed_url": "https://abaspeech.org/feed/",
                "website_url": "https://abaspeech.org",
                "description": "Blog sobre ABA e fonoaudiologia",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Full Spectrum ABA",
                "feed_url": "https://www.fullspectrumaba.com/blog-feed.xml",
                "website_url": "https://www.fullspectrumaba.com",
                "description": "Blog sobre ABA e autismo",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "ABA Everyday Blog",
                "feed_url": "https://abaeveryday.com/feed/",
                "website_url": "https://abaeveryday.com",
                "description": "Blog com dicas e recursos sobre ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Brighter Strides ABA",
                "feed_url": "https://www.brighterstridesaba.com/feed/",
                "website_url": "https://www.brighterstridesaba.com",
                "description": "Clínica de ABA - Blog",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Autism Spectrum News",
                "feed_url": "https://autismspectrumnews.org/feed",
                "website_url": "https://autismspectrumnews.org",
                "description": "Portal de notícias sobre autismo e ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Spectrum News",
                "feed_url": "https://www.spectrumnews.org/feed/",
                "website_url": "https://www.spectrumnews.org",
                "description": "Notícias sobre pesquisa em autismo",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Autism Parenting Magazine",
                "feed_url": "https://autismparentingmagazine.com/feed",
                "website_url": "https://autismparentingmagazine.com",
                "description": "Revista para pais sobre autismo e ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
        ],
    },
    "ABA Brasileira": {
        "description": "Feeds RSS de fontes brasileiras sobre Análise do Comportamento",
        "feeds": [
            {
                "name": "Boletim Contexto - ABPMC",
                "feed_url": "https://boletimcontexto.wordpress.com/feed/",
                "website_url": "https://boletimcontexto.wordpress.com",
                "description": "Boletim da Associação Brasileira de Psicologia e Medicina Comportamental",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Portal Comporte-se",
                "feed_url": "https://comportese.com/feed/",
                "website_url": "https://comportese.com",
                "description": "Portal de notícias e artigos sobre Análise do Comportamento",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Blog PGAC UEL",
                "feed_url": "http://analisedocomportamentouel.blogspot.com/feeds/posts/default",
                "website_url": "http://analisedocomportamentouel.blogspot.com",
                "description": "Blog do Programa de Pós-Graduação em Análise do Comportamento - UEL",
                "sync_frequency": SyncFrequency.WEEKLY,
            },
            {
                "name": "Blog AC Cultura PUC-SP",
                "feed_url": "https://accultura.wordpress.com/feed/",
                "website_url": "https://accultura.wordpress.com",
                "description": "Blog sobre Análise do Comportamento e Cultura - PUC-SP",
                "sync_frequency": SyncFrequency.WEEKLY,
            },
            {
                "name": "Blog OBM Brasil",
                "feed_url": "https://obmbrasil.wordpress.com/feed/",
                "website_url": "https://obmbrasil.wordpress.com",
                "description": "Blog sobre Behaviorismo Organizacional e Gestão - Brasil",
                "sync_frequency": SyncFrequency.WEEKLY,
            },
            {
                "name": "Blog do IEAC",
                "feed_url": "https://blog.ieac.net.br/feed",
                "website_url": "https://blog.ieac.net.br",
                "description": "Blog do Instituto de Ensino e Aplicação do Comportamento",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Genial Care Blog",
                "feed_url": "https://genialcare.com.br/blog/feed",
                "website_url": "https://genialcare.com.br",
                "description": "Blog sobre ABA e autismo",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "WayABA",
                "feed_url": "https://wayaba.com.br/feed",
                "website_url": "https://wayaba.com.br",
                "description": "Portal sobre ABA e autismo",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "ABA+ (ABA Mais)",
                "feed_url": "https://abamais.com/feed",
                "website_url": "https://abamais.com",
                "description": "Portal sobre ABA e desenvolvimento",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "ABA Fora da Mesinha",
                "feed_url": "https://abaforadamesinha.com.br/feed",
                "website_url": "https://abaforadamesinha.com.br",
                "description": "Blog sobre práticas em ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Blog ABAEDU",
                "feed_url": "https://www.abaedu.com.br/blog/feed",
                "website_url": "https://www.abaedu.com.br",
                "description": "Blog educacional sobre ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Canal Autismo / Revista Autismo",
                "feed_url": "https://www.canalautismo.com.br/feed",
                "website_url": "https://www.canalautismo.com.br",
                "description": "Portal de notícias sobre autismo no Brasil",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Autismo e Realidade",
                "feed_url": "https://autismoerealidade.org.br/feed",
                "website_url": "https://autismoerealidade.org.br",
                "description": "Organização sobre autismo e ABA",
                "sync_frequency": SyncFrequency.DAILY,
            },
            {
                "name": "Jornal da USP - Tag Autismo",
                "feed_url": "https://jornal.usp.br/tag/autismo/feed",
                "website_url": "https://jornal.usp.br",
                "description": "Notícias sobre autismo da USP",
                "sync_frequency": SyncFrequency.DAILY,
            },
        ],
    },
}


async def extract_domain(url: str) -> str:
    """Extrai o domínio de uma URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return "unknown"


async def create_or_update_feed(db, feed_data: dict) -> Feed:
    """Cria ou atualiza um feed no banco de dados."""
    # Verificar se já existe
    result = await db.execute(
        select(Feed).where(Feed.feed_url == feed_data["feed_url"])
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Atualizar feed existente
        for key, value in feed_data.items():
            if key != "feed_url":  # Não atualizar URL (é unique)
                setattr(existing, key, value)
        log.info(f"Feed atualizado: {existing.name}")
        return existing

    # Criar novo feed
    feed = Feed(
        name=feed_data["name"],
        feed_url=feed_data["feed_url"],
        feed_type=FeedType.RSS,
        website_url=feed_data.get("website_url"),
        description=feed_data.get("description"),
        is_active=True,
        sync_frequency=feed_data.get("sync_frequency", SyncFrequency.DAILY),
    )

    db.add(feed)
    await db.flush()
    log.info(f"Feed criado: {feed.name}")
    return feed


async def seed_feeds():
    """Popula o banco de dados com os feeds RSS."""
    setup_logging()
    log.info("=" * 60)
    log.info("Iniciando seed de feeds RSS...")
    log.info("=" * 60)

    # Inicializar banco
    try:
        await init_db()
        log.info("✓ Banco de dados inicializado")
    except Exception as e:
        log.error(f"✗ Erro ao inicializar banco: {e}")
        raise

    async with get_session_context() as db:
        total_created = 0
        total_updated = 0
        total_errors = 0

        for category_name, category_data in FEEDS_DATA.items():
            log.info(f"\n{'─' * 60}")
            log.info(f"Categoria: {category_name}")
            log.info(f"Descrição: {category_data['description']}")
            log.info(f"Total de feeds: {len(category_data['feeds'])}")
            log.info(f"{'─' * 60}")

            for idx, feed_data in enumerate(category_data["feeds"], 1):
                try:
                    # Validar dados obrigatórios
                    if not feed_data.get("feed_url") or not feed_data.get("name"):
                        log.warning(f"  [{idx}/{len(category_data['feeds'])}] Feed inválido: dados incompletos")
                        total_errors += 1
                        continue

                    # Verificar se já existe
                    result = await db.execute(
                        select(Feed).where(Feed.feed_url == feed_data["feed_url"])
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Atualizar
                        updated_fields = []
                        for key, value in feed_data.items():
                            if key != "feed_url" and hasattr(existing, key):
                                old_value = getattr(existing, key)
                                if old_value != value:
                                    setattr(existing, key, value)
                                    updated_fields.append(key)
                        
                        if updated_fields:
                            total_updated += 1
                            log.info(
                                f"  [{idx}/{len(category_data['feeds'])}] ✓ Atualizado: {feed_data['name']} "
                                f"(campos: {', '.join(updated_fields)})"
                            )
                        else:
                            log.debug(f"  [{idx}/{len(category_data['feeds'])}] → Já existe: {feed_data['name']}")
                    else:
                        # Criar novo
                        feed = Feed(
                            name=feed_data["name"],
                            feed_url=feed_data["feed_url"],
                            feed_type=FeedType.RSS,
                            website_url=feed_data.get("website_url"),
                            description=feed_data.get("description"),
                            is_active=True,
                            sync_frequency=feed_data.get(
                                "sync_frequency", SyncFrequency.DAILY
                            ),
                        )
                        db.add(feed)
                        total_created += 1
                        log.info(f"  [{idx}/{len(category_data['feeds'])}] + Criado: {feed_data['name']}")

                except Exception as e:
                    total_errors += 1
                    log.error(
                        f"  [{idx}/{len(category_data['feeds'])}] ✗ Erro ao processar "
                        f"{feed_data.get('name', 'feed')}: {e}",
                        exc_info=True,
                    )

        try:
            await db.commit()
            log.info(f"\n✓ Commit realizado com sucesso")
        except Exception as e:
            log.error(f"\n✗ Erro ao fazer commit: {e}")
            raise

        log.info(f"\n{'=' * 60}")
        log.info("RESUMO DO SEED")
        log.info(f"{'=' * 60}")
        log.info(f"  ✓ Feeds criados: {total_created}")
        log.info(f"  ↻ Feeds atualizados: {total_updated}")
        log.info(f"  ✗ Erros: {total_errors}")
        log.info(f"  📊 Total processado: {total_created + total_updated}")
        log.info(f"  📝 Total de feeds no sistema: {total_created + total_updated}")
        log.info(f"{'=' * 60}")
        
        if total_errors > 0:
            log.warning(f"\n⚠ Atenção: {total_errors} feed(s) apresentaram erros. Revise os logs acima.")


async def main():
    """Função principal."""
    try:
        await seed_feeds()
    except Exception as e:
        log.error(f"Erro ao executar seed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

