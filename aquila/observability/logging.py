from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger("aquila")
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"aquila.{name}")
