"""Lightweight in-process telemetry collector — counters + latency timers."""

from __future__ import annotations

import time
from collections import defaultdict


class Telemetry:
    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)
        self.latencies_ms: dict[str, list[float]] = defaultdict(list)

    def incr(self, name: str, n: int = 1) -> None:
        self.counters[name] += n

    def time(self, name: str):
        return _Timer(self, name)

    def snapshot(self) -> dict:
        return {
            "counters": dict(self.counters),
            "latencies_ms_p50": {
                k: sorted(v)[len(v) // 2] if v else 0.0 for k, v in self.latencies_ms.items()
            },
        }


class _Timer:
    def __init__(self, t: Telemetry, name: str) -> None:
        self._t = t
        self._name = name
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self._t.latencies_ms[self._name].append((time.perf_counter() - self._start) * 1000.0)
        return False
