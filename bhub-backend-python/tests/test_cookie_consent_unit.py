"""Testes do módulo de consentimento de cookies e configurações de privacidade."""

from app.config import Settings


def test_analytics_desativado_por_padrao(monkeypatch):
    """enable_analytics deve ser False por padrão (privacidade por design)."""
    monkeypatch.delenv("ENABLE_ANALYTICS", raising=False)
    s = Settings(_env_file=None)
    assert s.enable_analytics is False


def test_settings_de_consentimento_existem():
    s = Settings(_env_file=None)
    assert s.cookie_consent_enabled is True
    assert s.cookie_consent_version == "1.0"
    assert s.analytics_respect_dnt is True
