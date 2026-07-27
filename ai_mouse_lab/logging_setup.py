from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import LOGS_DIR, ensure_data_dirs


def configure_logging() -> logging.Logger:
    ensure_data_dirs()
    logger = logging.getLogger("ai_mouse_lab")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=2_000_000,
        backupCount=4,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    return logger
