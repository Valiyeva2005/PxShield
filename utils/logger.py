"""
PixelShield – Logging Utilities
Centralised Loguru-based logger with file rotation and Rich-compatible formatting.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_INITIALISED: set[str] = set()


def get_logger(name: str = "pixelshield", log_dir: str | Path = "logs") -> "logger":
    """Return a configured Loguru logger bound to *name*.

    Sinks are added only once per *name* so repeated calls are safe.

    Args:
        name:    Contextual name used as a log-file prefix.
        log_dir: Directory where rotating log files are written.

    Returns:
        A bound Loguru logger instance.
    """
    if name in _INITIALISED:
        return logger.bind(context=name)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove the default stderr sink so Rich controls console output.
    logger.remove()

    # Console sink – concise, coloured.
    logger.add(
        sys.stderr,
        level="WARNING",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # File sink for this context.
    logger.add(
        log_path / f"{name}.log",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
        enqueue=True,
    )

    _INITIALISED.add(name)
    return logger.bind(context=name)


# Convenience pre-configured loggers.
encrypt_logger = get_logger("encrypt")
decrypt_logger = get_logger("decrypt")
