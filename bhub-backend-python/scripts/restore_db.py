#!/usr/bin/env python3
"""
Script para restaurar backup do banco de dados SQLite.
"""

import argparse
import shutil
import sqlite3
from pathlib import Path

from app.config import settings
from app.core.logging import log, setup_logging


def verify_backup_integrity(backup_path: Path) -> bool:
    """
    Verifica a integridade de um backup.

    Returns:
        True se o backup está íntegro, False caso contrário
    """
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()

        # Executar verificação de integridade
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        conn.close()

        if result and result[0] == "ok":
            return True
        else:
            log.error(f"Integridade do backup falhou: {result}")
            return False

    except Exception as e:
        log.error(f"Erro ao verificar integridade do backup: {e}")
        return False


def restore_database(
    backup_path: Path,
    db_path: Path,
    verify: bool = True,
    create_backup: bool = True,
) -> bool:
    """
    Restaura banco de dados a partir de um backup.

    Args:
        backup_path: Caminho do arquivo de backup
        db_path: Caminho do banco de dados a restaurar
        verify: Se True, verifica integridade do backup antes de restaurar
        create_backup: Se True, cria backup do banco atual antes de restaurar

    Returns:
        True se restauração foi bem-sucedida, False caso contrário
    """
    if not backup_path.exists():
        log.error(f"Backup não encontrado: {backup_path}")
        return False

    # Verificar integridade do backup
    if verify:
        log.info("Verificando integridade do backup...")
        if not verify_backup_integrity(backup_path):
            log.error("Restauração cancelada: backup corrompido")
            return False

    # Criar backup do banco atual se existir
    if create_backup and db_path.exists():
        from datetime import datetime

        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        current_backup = backup_dir / f"bhub_pre_restore_{timestamp}.db"

        log.info(f"Criando backup do banco atual: {current_backup.name}")
        shutil.copy2(db_path, current_backup)
        log.info(f"Backup do banco atual criado: {current_backup}")

    try:
        # Parar aplicação se estiver rodando (responsabilidade do operador)
        log.warning("Certifique-se de que a aplicação está parada antes de restaurar!")

        # Restaurar usando SQLite backup API
        backup_conn = sqlite3.connect(str(backup_path))
        db_conn = sqlite3.connect(str(db_path))

        backup_conn.backup(db_conn)

        backup_conn.close()
        db_conn.close()

        # Verificar integridade do banco restaurado
        if verify:
            log.info("Verificando integridade do banco restaurado...")
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == "ok":
                log.info("Banco de dados restaurado com sucesso")
                return True
            else:
                log.error(f"Banco restaurado está corrompido: {result}")
                return False
        else:
            log.info("Banco de dados restaurado com sucesso")
            return True

    except Exception as e:
        log.error(f"Erro ao restaurar backup: {e}")
        return False


def list_backups(backup_dir: Path) -> list[Path]:
    """
    Lista backups disponíveis.

    Returns:
        Lista de caminhos de backups ordenados por data (mais recente primeiro)
    """
    if not backup_dir.exists():
        return []

    backups = sorted(
        backup_dir.glob("bhub_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return backups


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Restaurar backup do banco de dados BHUB")
    parser.add_argument(
        "backup_path",
        type=Path,
        help="Caminho do arquivo de backup a restaurar",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path(settings.base_dir) / "bhub.db",
        help="Caminho do banco de dados a restaurar",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Não verificar integridade antes de restaurar",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Não criar backup do banco atual antes de restaurar",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Listar backups disponíveis",
    )

    args = parser.parse_args()

    setup_logging()

    # Listar backups se solicitado
    if args.list:
        backup_dir = args.backup_path if args.backup_path.is_dir() else args.backup_path.parent
        backups = list_backups(backup_dir)

        if backups:
            print(f"\nBackups disponíveis em {backup_dir}:")
            for backup in backups:
                from datetime import datetime
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                size = backup.stat().st_size / 1024 / 1024
                print(f"  - {backup.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')}, {size:.2f} MB)")
        else:
            print(f"Nenhum backup encontrado em {backup_dir}")
        return 0

    # Restaurar
    log.info(f"Iniciando restauração do backup: {args.backup_path}")

    success = restore_database(
        backup_path=args.backup_path,
        db_path=args.db_path,
        verify=not args.no_verify,
        create_backup=not args.no_backup,
    )

    if success:
        log.info("Restauração concluída com sucesso")
        print("Restauração concluída com sucesso")
        print(f"Banco restaurado: {args.db_path}")
        return 0
    else:
        log.error("Restauração falhou")
        print("Restauração falhou - verifique os logs")
        return 1


if __name__ == "__main__":
    exit(main())
