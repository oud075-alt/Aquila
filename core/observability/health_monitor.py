"""Health monitor — tracks freshness, latency, confidence degradation, stale data.

Provides a single `HealthSnapshot` consumed by `/health` and `/system/status`.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from core.observability.metrics import MetricsRegistry, default_registry


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    healthy: bool
    last_diagnosis_at: datetime | None
    last_ingestion_at: datetime | None
    diagnosis_latency_ms: float
    ingestion_latency_ms: float
    orchestration_latency_ms: float
    confidence_degradation: float
    stale_warnings: int
    memory_warnings: int
    uptime_seconds: float
    counters: Mapping[str, float]


class HealthMonitor:
    """Aggregates timing samples and stale/memory warnings."""

    def __init__(self, registry: MetricsRegistry | None = None) -> None:
        self.registry = registry or default_registry
        self._started_at = time.perf_counter()
        self._last_diagnosis_at: datetime | None = None
        self._last_ingestion_at: datetime | None = None
        self._last_confidence: float = 1.0
        self._confidence_ewma: float = 1.0
        self._confidence_alpha: float = 0.05
        self._stale_warnings: int = 0
        self._memory_warnings: int = 0

    def record_diagnosis(self, *, latency_ms: float, confidence: float) -> None:
        now = datetime.now(tz=UTC)
        self._last_diagnosis_at = now
        self._last_confidence = confidence
        self._confidence_ewma = (
            (1.0 - self._confidence_alpha) * self._confidence_ewma
            + self._confidence_alpha * confidence
        )
        self.registry.observe("diagnosis_latency_ms", latency_ms)
        self.registry.observe("global_confidence", confidence)

    def record_ingestion(self, *, latency_ms: float) -> None:
        self._last_ingestion_at = datetime.now(tz=UTC)
        self.registry.observe("ingestion_latency_ms", latency_ms)

    def record_orchestration(self, *, latency_ms: float) -> None:
        self.registry.observe("orchestration_latency_ms", latency_ms)

    def record_stale_warning(self, count: int = 1) -> None:
        self._stale_warnings += count
        self.registry.incr("stale_warnings", count)

    def record_memory_warning(self, count: int = 1) -> None:
        self._memory_warnings += count
        self.registry.incr("memory_warnings", count)

    def snapshot(self) -> HealthSnapshot:
        s = self.registry.snapshot()
        hist_obj = s["histograms"]
        counters_obj = s["counters"]
        assert isinstance(hist_obj, dict)
        assert isinstance(counters_obj, dict)
        diag_mean = float(hist_obj.get("diagnosis_latency_ms", {}).get("mean", 0.0))
        ing_mean = float(hist_obj.get("ingestion_latency_ms", {}).get("mean", 0.0))
        orch_mean = float(hist_obj.get("orchestration_latency_ms", {}).get("mean", 0.0))
        counters: Mapping[str, float] = {str(k): float(v) for k, v in counters_obj.items()}
        degradation = max(0.0, 1.0 - self._confidence_ewma)
        return HealthSnapshot(
            healthy=self._last_diagnosis_at is not None,
            last_diagnosis_at=self._last_diagnosis_at,
            last_ingestion_at=self._last_ingestion_at,
            diagnosis_latency_ms=diag_mean,
            ingestion_latency_ms=ing_mean,
            orchestration_latency_ms=orch_mean,
            confidence_degradation=degradation,
            stale_warnings=self._stale_warnings,
            memory_warnings=self._memory_warnings,
            uptime_seconds=time.perf_counter() - self._started_at,
            counters=counters,
        )
