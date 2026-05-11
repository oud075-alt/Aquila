"""Phase 0G — Observability substrate.

structlog-based JSON logging, in-process metrics registry,
OpenTelemetry-compatible trace context, and health monitor.
"""

from core.observability.health_monitor import HealthMonitor, HealthSnapshot
from core.observability.logger import get_logger, init_logging
from core.observability.metrics import (
    Histogram,
    MetricsRegistry,
    default_registry,
)
from core.observability.trace_context import TraceContext, current_trace, traced

__all__ = [
    "HealthMonitor",
    "HealthSnapshot",
    "Histogram",
    "MetricsRegistry",
    "TraceContext",
    "current_trace",
    "default_registry",
    "get_logger",
    "init_logging",
    "traced",
]
