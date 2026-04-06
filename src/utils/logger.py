"""
Configuração centralizada de logs com loguru.
"""

import sys
from loguru import logger as _logger
from src.utils.config import LOG_LEVEL, LOG_FILE

# Re-exporta logger com nome explícito para facilitar análise estática.
logger = _logger


def setup_logger() -> None:
    """Configura o logger global do projeto."""
    logger.remove()

    # Console — colorido e legível
    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Arquivo — rotação diária, mantém 30 dias
    logger.add(
        LOG_FILE,
        level=LOG_LEVEL,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | {name}:{line} — {message}"
        ),
        rotation="1 day",
        retention="30 days",
        encoding="utf-8",
    )


setup_logger()

__all__ = ["logger"]
