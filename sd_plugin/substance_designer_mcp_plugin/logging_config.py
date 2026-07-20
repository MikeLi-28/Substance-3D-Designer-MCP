"""Rotating plugin logs that never contain session tokens or material payloads."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_plugin_logging(path: Path, level: str = "INFO") -> logging.Logger:
    """Configure one rotating file logger and return it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("substance_designer_mcp_plugin")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    handler = RotatingFileHandler(str(path), maxBytes=1_048_576, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
