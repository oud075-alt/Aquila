"""Falsification test for Assumption ``structural.bar_closed_data``.

Claim: L2 operates on bar-closed OHLCV. Therefore, given the same
*closed* bar fed through the structural layer twice, the diagnosis state
and score must be identical. If they ever differ, the layer is silently
consuming non-closed/intra-bar data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aquila.core.base import LayerContext
from aquila.core.types import LayerName, Symbol
from aquila.primitives import PrimitiveBar
from aquila.primitives.service import PrimitiveMetricsLayer
from aquila.structural.service import StructuralDiagnosisLayer


def _bars() -> list[PrimitiveBar]:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        PrimitiveBar(
            timestamp=t0 + timedelta(minutes=i),
            open=100.0 + i * 0.1,
            high=100.5 + i * 0.1,
            low=99.5 + i * 0.1,
            close=100.2 + i * 0.1,
            volume=10.0,
        )
        for i in range(5)
    ]


def _run(bars: list[PrimitiveBar]):
    prim = PrimitiveMetricsLayer()
    struct = StructuralDiagnosisLayer()
    sym = Symbol("X")
    ctx = LayerContext(correlation_id="c", symbol=sym)
    snap_out = None
    diag_out = None
    for b in bars:
        snap_out = prim.process(b, ctx)
        ctx.record(snap_out)
        diag_out = struct.process(snap_out.payload, ctx)
        ctx.record(diag_out)
    return snap_out, diag_out


def test_intra_bar_does_not_change_diagnosis():
    bars = _bars()
    snap_a, diag_a = _run(bars)
    snap_b, diag_b = _run(bars)
    assert diag_a is not None and diag_b is not None
    assert diag_a.payload.state == diag_b.payload.state
    assert diag_a.payload.score == diag_b.payload.score
    assert snap_a.payload.range_pct == snap_b.payload.range_pct
