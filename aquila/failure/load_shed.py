"""Load-shedding policy. Closes audit gap #57.

When telemetry shows cycle latency > budget, optional layers (intermarket,
attention, narrative emission) are skipped to preserve core cognition.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadShedPolicy:
    cycle_latency_budget_ms: float = 250.0

    def should_shed(self, p50_latency_ms: float) -> bool:
        return p50_latency_ms > self.cycle_latency_budget_ms
