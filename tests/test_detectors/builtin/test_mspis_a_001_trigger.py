"""Structural / behavioural tests for the MSPIS-A-001 trigger function.

Per HARD RULE #6 these tests must NOT assert precision/recall of the
detector. They test that:

- the detector is a valid first-class object;
- the trigger function returns ``False`` before warm-up;
- the trigger function returns ``True`` for the canonical "top decile
  range + thin volume" shape after warm-up;
- the trigger function does not leak state across resets.
"""

from __future__ import annotations

from aquila.core.base import LayerContext
from aquila.core.types import LayerName, Symbol
from aquila.detectors import DetectorRegistry
from aquila.detectors.builtin.mspis_a_001 import (
    DEFINITION,
    MIN_WARMUP,
    reset_state,
    trigger,
)
from aquila.primitives.schemas import PrimitiveSnapshot


def _ctx() -> LayerContext:
    return LayerContext(correlation_id="c", symbol=Symbol("X"))


def _snap(range_pct: float, volume_z: float = -1.0) -> PrimitiveSnapshot:
    return PrimitiveSnapshot(
        bars_seen=100,
        last_close=100.0,
        range_pct=range_pct,
        volume_z=volume_z,
    )


def test_definition_is_first_class():
    assert DEFINITION.anomaly_id == "MSPIS-A-001"
    assert DEFINITION.version == "0.1.0"
    assert DEFINITION.outcome_rule.horizon_bars == 10
    assert "abs(realized_return)" in DEFINITION.outcome_rule.success_expression
    assert DEFINITION.success_metric.baseline == "random_bar_sampler"
    assert LayerName.PRIMITIVES in DEFINITION.inputs_required


def test_definition_registers_cleanly():
    reg = DetectorRegistry()
    reg.register(DEFINITION, trigger)
    assert len(reg) == 1
    d, fn = reg.get("MSPIS-A-001", "0.1.0")
    assert d is DEFINITION
    assert fn is trigger


def test_before_warmup_never_fires():
    reset_state()
    ctx = _ctx()
    for _ in range(MIN_WARMUP - 1):
        assert trigger(_snap(0.05, volume_z=-2.0), ctx) is False


def test_top_decile_thin_volume_fires_after_warmup():
    reset_state()
    ctx = _ctx()
    for _ in range(MIN_WARMUP + 20):
        trigger(_snap(0.005, volume_z=0.0), ctx)
    fired = trigger(_snap(0.05, volume_z=-1.0), ctx)
    assert fired is True


def test_high_volume_does_not_fire():
    reset_state()
    ctx = _ctx()
    for _ in range(MIN_WARMUP + 20):
        trigger(_snap(0.005, volume_z=0.0), ctx)
    fired = trigger(_snap(0.05, volume_z=1.0), ctx)
    assert fired is False


def test_reset_state_clears_history():
    reset_state()
    ctx = _ctx()
    for _ in range(MIN_WARMUP + 20):
        trigger(_snap(0.005, volume_z=0.0), ctx)
    reset_state()
    assert trigger(_snap(0.05, volume_z=-1.0), ctx) is False
