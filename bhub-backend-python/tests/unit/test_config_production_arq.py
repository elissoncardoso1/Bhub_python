"""Configuração de produção exige ARQ (jobs persistentes).

F1 / R19-1: ``production + ENABLE_ARQ=false`` era aceito e ``get_task_queue()``
caía no ``InlineTaskQueue`` — executor local não persistente. Produção exige
Redis + ARQ (ADR-0002); o executor inline continua válido fora de produção.

``test`` NÃO é um environment válido neste projeto (``app/config.py:28`` lista
apenas development/staging/production). A suíte roda como ``development``, que é
o default — não criamos um segundo conceito de environment para cobrir o caso.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings

PROD = {
    "environment": "production",
    "secret_key": "k" * 40,
    "allowed_origins": "https://bhub.example",
}


def test_producao_com_arq_desabilitado_e_rejeitada():
    """RED antes do fix: a combinação era aceita e selecionava a fila inline."""
    with pytest.raises(ValidationError, match="ENABLE_ARQ"):
        Settings(**PROD, enable_arq=False)


def test_producao_sem_arq_no_ambiente_usa_o_default_false_e_e_rejeitada(monkeypatch):
    """Ausente/default ``false`` (``app/config.py:63``) também é rejeitado."""
    monkeypatch.delenv("ENABLE_ARQ", raising=False)
    with pytest.raises(ValidationError, match="ENABLE_ARQ"):
        Settings(**PROD)


def test_producao_com_arq_habilitado_e_valida():
    s = Settings(**PROD, enable_arq=True)
    assert s.is_production is True
    assert s.enable_arq is True


@pytest.mark.parametrize("env", ["development", "staging"])
def test_fora_de_producao_o_executor_inline_continua_valido(env):
    """O fix não pode eliminar o workflow inline de dev/test."""
    s = Settings(
        environment=env,
        secret_key="k" * 40,
        allowed_origins="https://bhub.example",
        enable_arq=False,
    )
    assert s.enable_arq is False


def test_test_nao_e_um_environment_valido():
    """Documenta o mapeamento honesto do caso ``test`` do plano."""
    with pytest.raises(ValidationError):
        Settings(environment="test", enable_arq=False)
