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


# --- Desativação por max_errors não pode virar morte permanente ------------
# `_record_fetch_failure` agora desativa o feed ao atingir `max_errors`
# (defeito D2 do incidente de 2026-09-22). A desativação só é aceitável porque
# a sonda de recuperação continua valendo — e porque o sync bem-sucedido
# reativa o feed. Sem isso, a "sonda de recuperação" seria decorativa: o feed
# zeraria error_count e ficaria inativo para sempre.


def test_feed_desativado_por_erro_ainda_elegivel_na_sonda():
    feed = make_feed(error_count=5, last_sync_at=datetime.utcnow() - timedelta(days=8))
    feed.is_active = False
    feed.deactivated_by_errors = True
    assert feed.needs_sync is True


def test_feed_desativado_por_erro_nao_sincroniza_antes_da_sonda():
    feed = make_feed(error_count=5, last_sync_at=datetime.utcnow() - timedelta(hours=2))
    feed.is_active = False
    feed.deactivated_by_errors = True
    assert feed.needs_sync is False


def test_feed_desativado_manualmente_nao_sincroniza_nunca():
    """Curadoria desativa um feed sem erros: ele deve ficar fora, sem sonda."""
    feed = make_feed(error_count=0, last_sync_at=datetime.utcnow() - timedelta(days=365))
    feed.is_active = False
    feed.deactivated_by_errors = False
    assert feed.needs_sync is False


def test_desativado_manualmente_nao_e_ressuscitado_nem_com_erros():
    """O marcador protege a decisão humana: errar não reativa por tabela."""
    feed = make_feed(error_count=9, last_sync_at=datetime.utcnow() - timedelta(days=99))
    feed.is_active = False
    feed.deactivated_by_errors = False
    assert feed.needs_sync is False


def test_exhausted_errors_descreve_o_limite():
    assert make_feed(error_count=4).exhausted_errors is False
    assert make_feed(error_count=5).exhausted_errors is True
    assert make_feed(error_count=16).exhausted_errors is True
