"""Baseline detector tests — rate calibration and determinism."""

from __future__ import annotations

from datetime import datetime, timezone

from aquila.core.base import LayerContext
from aquila.core.types import Symbol
from aquila.detectors import RandomBarSampler
from aquila.primitives.schemas import PrimitiveSnapshot


def _ctx() -> LayerContext:
    return LayerContext(correlation_id="c", symbol=Symbol("X"))


def _snap() -> PrimitiveSnapshot:
    return PrimitiveSnapshot(bars_seen=10, last_close=100.0)


def test_random_sampler_rate_within_tolerance():
    sampler = RandomBarSampler(seed=42, target_rate=0.1)
    fires = sum(1 for _ in range(10_000) if sampler.fire(_snap(), _ctx()))
    rate = fires / 10_000
    assert 0.085 <= rate <= 0.115


def test_random_sampler_reproducible_with_seed():
    a = RandomBarSampler(seed=7, target_rate=0.05)
    b = RandomBarSampler(seed=7, target_rate=0.05)
    seq_a = [a.fire(_snap(), _ctx()) for _ in range(1000)]
    seq_b = [b.fire(_snap(), _ctx()) for _ in range(1000)]
    assert seq_a == seq_b


def test_random_sampler_zero_rate_never_fires():
    sampler = RandomBarSampler(seed=1, target_rate=0.0)
    assert not any(sampler.fire(_snap(), _ctx()) for _ in range(1000))


def test_random_sampler_full_rate_always_fires():
    sampler = RandomBarSampler(seed=1, target_rate=1.0)
    assert all(sampler.fire(_snap(), _ctx()) for _ in range(1000))
