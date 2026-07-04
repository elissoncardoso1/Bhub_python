"""Testes da sonda de recuperação de feeds com erro."""

from datetime import datetime, timedelta

from app.models.feed import Feed, SyncFrequency


def make_feed(error_count: int = 0, last_sync_at: datetime | None = None) -> Feed:
    feed = Feed(name="teste", feed_url="https://example.com/feed")
    feed.is_active = True
    feed.error_count = error_count
    feed.max_errors = 5
    feed.sync_frequency = SyncFrequency.HOURLY
    feed.last_sync_at = last_sync_at
    return feed


def test_feed_saudavel_precisa_sync_apos_intervalo():
    feed = make_feed(last_sync_at=datetime.utcnow() - timedelta(hours=2))
    assert feed.needs_sync is True


def test_feed_com_erros_recentes_nao_sincroniza():
    feed = make_feed(error_count=5, last_sync_at=datetime.utcnow() - timedelta(hours=2))
    assert feed.needs_sync is False


def test_feed_com_erros_antigos_entra_em_sonda_de_recuperacao():
    feed = make_feed(error_count=5, last_sync_at=datetime.utcnow() - timedelta(days=8))
    assert feed.needs_sync is True
