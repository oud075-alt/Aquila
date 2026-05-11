"""In-process metrics registry with counters and histograms.

Exposed via `/metrics` API in Phase 0H. Histograms are streaming
Welford-style estimators to keep memory bounded.
"""

from __future__ import annotations

import math
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class _Welford:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    min_: float = math.inf
    max_: float = -math.inf

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2
        self.min_ = min(self.min_, x)
        self.max_ = max(self.max_, x)

    @property
    def variance(self) -> float:
        return self.m2 / self.n if self.n > 1 else 0.0

    @property
    def stddev(self) -> float:
        return math.sqrt(self.variance)


@dataclass(slots=True)
class Histogram:
    name: str
    estimator: _Welford = field(default_factory=_Welford)

    def observe(self, value: float) -> None:
        self.estimator.update(float(value))

    def snapshot(self) -> dict[str, float]:
        e = self.estimator
        return {
            "count": float(e.n),
            "mean": e.mean,
            "stddev": e.stddev,
            "min": 0.0 if e.n == 0 else e.min_,
            "max": 0.0 if e.n == 0 else e.max_,
        }


class MetricsRegistry:
    """Thread-safe in-process counter + histogram registry."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def incr(self, name: str, amount: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += float(amount)

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            h = self._histograms.get(name)
            if h is None:
                h = Histogram(name=name)
                self._histograms[name] = h
            h.observe(value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "histograms": {n: h.snapshot() for n, h in self._histograms.items()},
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()

    def counter_names(self) -> Iterable[str]:
        with self._lock:
            return tuple(self._counters.keys())


default_registry: MetricsRegistry = MetricsRegistry()
