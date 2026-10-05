"""Application-wide logging setup (console + rotating file in logs/)."""

import logging
from logging.handlers import RotatingFileHandler

from config import settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.logs_dir / "slayin.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.addHandler(console)
    root.addHandler(file_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
