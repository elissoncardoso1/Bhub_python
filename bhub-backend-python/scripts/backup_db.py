#!/usr/bin/env python3
"""
Script para backup automático do banco de dados SQLite.
"""

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.core.logging import log, setup_logging


def verify_database_integrity(db_path: Path) -> bool:
    """
    Verifica a integridade do banco de dados.

    Returns:
        True se o banco está íntegro, False caso contrário
    """
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Executar verificação de integridade
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        conn.close()

        if result and result[0] == "ok":
            return True
        else:
            log.error(f"Integridade do banco falhou: {result}")
            return False

    except Exception as e:
        log.error(f"Erro ao verificar integridade: {e}")
        return False


def get_backup_path(base_path: Path, retention_days: int = 30) -> Path:
    """
    Gera caminho para backup com timestamp.

    Args:
        base_path: Diretório base para backups
        retention_days: Dias de retenção (não usado aqui, mas para referência)

    Returns:
        Caminho completo do arquivo de backup
    """
    base_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"bhub_backup_{timestamp}.db"

    return base_path / backup_filename


def cleanup_old_backups(backup_dir: Path, retention_days: int = 30) -> int:
    """
    Remove backups antigos além do período de retenção.

    Returns:
        Número de backups removidos
    """
    if not backup_dir.exists():
        return 0

    cutoff_date = datetime.utcnow().timestamp() - (retention_days * 24 * 60 * 60)
    removed = 0

    for backup_file in backup_dir.glob("bhub_backup_*.db"):
        if backup_file.stat().st_mtime < cutoff_date:
            try:
                backup_file.unlink()
                removed += 1
                log.info(f"Backup antigo removido: {backup_file.name}")
            except Exception as e:
                log.error(f"Erro ao remover backup {backup_file.name}: {e}")

    return removed


def backup_database(
    db_path: Path,
    backup_dir: Path,
    verify: bool = True,
    retention_days: int = 30,
) -> Path | None:
    """
    Cria backup do banco de dados SQLite.

    Args:
        db_path: Caminho do banco de dados
        backup_dir: Diretório para salvar backups
        verify: Se True, verifica integridade antes do backup
        retention_days: Dias de retenção de backups

    Returns:
        Caminho do backup criado ou None se falhou
    """
    if not db_path.exists():
        log.error(f"Banco de dados não encontrado: {db_path}")
        return None

    # Verificar integridade
    if verify:
        log.info("Verificando integridade do banco de dados...")
        if not verify_database_integrity(db_path):
            log.error("Backup cancelado: banco de dados corrompido")
            return None

    # Gerar caminho do backup
    backup_path = get_backup_path(backup_dir)

    try:
        # Criar backup usando SQLite backup API
        source_conn = sqlite3.connect(str(db_path))
        backup_conn = sqlite3.connect(str(backup_path))

        source_conn.backup(backup_conn)

        source_conn.close()
        backup_conn.close()

        # Verificar tamanho do backup
        backup_size = backup_path.stat().st_size
        log.info(f"Backup criado: {backup_path.name} ({backup_size / 1024 / 1024:.2f} MB)")

        # Limpar backups antigos
        removed = cleanup_old_backups(backup_dir, retention_days)
        if removed > 0:
            log.info(f"{removed} backups antigos removidos")

        return backup_path

    except Exception as e:
        log.error(f"Erro ao criar backup: {e}")
        # Remover backup parcial se existir
        if backup_path.exists():
            backup_path.unlink()
        return None


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Backup do banco de dados BHUB")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path(settings.base_dir) / "bhub.db",
        help="Caminho do banco de dados",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(settings.base_dir) / "backups",
        help="Diretório para backups",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Não verificar integridade antes do backup",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Dias de retenção de backups (default: 30)",
    )

    args = parser.parse_args()

    setup_logging()

    log.info("Iniciando backup do banco de dados...")

    backup_path = backup_database(
        db_path=args.db_path,
        backup_dir=args.backup_dir,
        verify=not args.no_verify,
        retention_days=args.retention_days,
    )

    if backup_path:
        log.info(f"Backup concluído com sucesso: {backup_path}")
        print(f"Backup criado: {backup_path}")
        return 0
    else:
        log.error("Backup falhou")
        print("Backup falhou - verifique os logs")
        return 1


if __name__ == "__main__":
    exit(main())
