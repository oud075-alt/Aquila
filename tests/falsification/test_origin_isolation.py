"""Falsification test for Assumption ``memory.origin_isolation``.

Claim: synthetic / replay-origin events MUST NOT write to the real
memory archive. If the archive grows after a synthetic-origin tick, the
isolation invariant is broken.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aquila.core.base import LayerContext
from aquila.core.types import LayerName, Symbol
from aquila.memory.engine import EpisodicMemoryLayer
from aquila.pathology.service import PathologyContradictionLayer
from aquila.primitives import PrimitiveBar
from aquila.primitives.service import PrimitiveMetricsLayer
from aquila.structural.service import StructuralDiagnosisLayer


def _bars(n: int = 10) -> list[PrimitiveBar]:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = []
    for i in range(n):
        bars.append(PrimitiveBar(
            timestamp=t0 + timedelta(minutes=i),
            open=100.0 + i * 0.1,
            high=101.0 + i * 0.1,
            low=99.5 + i * 0.1,
            close=100.5 + i * 0.1,
            volume=10.0,
        ))
    return bars


def test_synthetic_never_writes_real_archive():
    prim = PrimitiveMetricsLayer()
    struct = StructuralDiagnosisLayer()
    path = PathologyContradictionLayer()
    mem = EpisodicMemoryLayer(write_on_real=True)

    sym = Symbol("X")
    for b in _bars():
        ctx = LayerContext(correlation_id="c", symbol=sym, origin="synthetic")
        snap = prim.process(b, ctx); ctx.record(snap)
        diag = struct.process(snap.payload, ctx); ctx.record(diag)
        prep = path.process(diag.payload, ctx); ctx.record(prep)
        mem_out = mem.process(prep.payload, ctx); ctx.record(mem_out)
        assert mem_out.payload.written is False

    assert mem.archive.size() == 0
