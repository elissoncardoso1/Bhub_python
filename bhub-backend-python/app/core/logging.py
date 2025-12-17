"""
Configuração de logging com Loguru.
"""

import sys
from pathlib import Path

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    """Configura o sistema de logging."""
    # Remove handler padrão
    logger.remove()

    # Formato do log
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Handler para console
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )

    # Handler para arquivo combinado
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "combined.log",
        format=log_format,
        level="DEBUG",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="gz",
        enqueue=True,  # Thread-safe
    )

    # Handler para erros
    logger.add(
        log_dir / "error.log",
        format=log_format,
        level="ERROR",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="gz",
        enqueue=True,
    )

    # Handler para sync de feeds
    logger.add(
        log_dir / "feed_sync.log",
        format=log_format,
        level="INFO",
        rotation="1 day",
        retention="1 month",
        filter=lambda record: "feed_sync" in record["extra"],
        enqueue=True,
    )

    logger.info("Logging configurado com sucesso")


def get_logger(name: str = "bhub"):
    """Retorna logger com contexto."""
    return logger.bind(name=name)


# Logger pré-configurado para uso direto
log = get_logger()
