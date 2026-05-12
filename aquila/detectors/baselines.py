"""Null baselines for anomaly detector evaluation.

A detector is only meaningful if it beats a deliberately-uninformed
baseline. ``RandomBarSampler`` fires at uniform random with a configured
target rate, matched to the detector's own trigger rate.
"""

from __future__ import annotations

import random
from typing import Protocol

from aquila.core.base import LayerContext
from aquila.primitives.schemas import PrimitiveSnapshot


class BaselineDetector(Protocol):
    """A null baseline that mimics a detector's *rate* but not its content."""

    name: str

    def reset(self, *, seed: int = 0, target_rate: float = 0.01) -> None: ...

    def fire(self, snap: PrimitiveSnapshot, ctx: LayerContext) -> bool: ...


class RandomBarSampler:
    """Uniform-random trigger at a configurable rate."""

    name: str = "random_bar_sampler"

    def __init__(self, *, seed: int = 0, target_rate: float = 0.01) -> None:
        self._rng = random.Random(seed)
        self._rate = max(0.0, min(1.0, target_rate))

    def reset(self, *, seed: int = 0, target_rate: float = 0.01) -> None:
        self._rng = random.Random(seed)
        self._rate = max(0.0, min(1.0, target_rate))

    def fire(self, snap: PrimitiveSnapshot, ctx: LayerContext) -> bool:
        return self._rng.random() < self._rate
