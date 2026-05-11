"""Resource governance — replay compute budgets, retention policies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceBudget:
    max_replay_ticks: int = 1_000_000
    max_memory_episodes: int = 100_000
    max_cycle_latency_ms: float = 250.0
