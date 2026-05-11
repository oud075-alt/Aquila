"""Centralised structured logging helpers for MSPIS."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from config import get_settings


_INITIALISED: dict[str, logging.Logger] = {}


def get_logger(name: str, file: Optional[str] = None) -> logging.Logger:
    """Return a configured logger, creating it once per process."""
    if name in _INITIALISED:
        return _INITIALISED[name]

    settings = get_settings()
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-32s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    log_path: Path
    if file:
        log_path = settings.logs_dir / file
    else:
        log_path = settings.logs_dir / "mspis.log"
    try:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        # File system might be read-only in some hosts; degrade silently.
        pass

    _INITIALISED[name] = logger
    return logger
