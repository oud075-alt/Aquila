"""Structured JSON logging via structlog."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

_INITIALIZED: bool = False


def _add_service(_: Any, __: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("service", "mspis")
    return event_dict


def init_logging(*, level: str = "INFO") -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    _INITIALIZED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    if not _INITIALIZED:
        init_logging()
    return structlog.get_logger(name) if name else structlog.get_logger()
