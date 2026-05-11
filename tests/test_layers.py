from __future__ import annotations

from aquila.core.types import LayerName
from aquila.deception import DeceptionIntelligenceLayer
from aquila.memory import EpisodicMemoryLayer
from aquila.meta import MetaCognitionLayer
from aquila.pathology import PathologyContradictionLayer
from aquila.primitives import PrimitiveMetricsLayer
from aquila.regime import RegimeMutationLayer
from aquila.structural import StructuralDiagnosisLayer
from aquila.temporal import TemporalHierarchyLayer


def _run_through(bars, ctx):
    p = PrimitiveMetricsLayer(window=20)
    s = StructuralDiagnosisLayer()
    pa = PathologyContradictionLayer()
    mem = EpisodicMemoryLayer()
    temp = TemporalHierarchyLayer()
    decep = DeceptionIntelligenceLayer()
    reg = RegimeMutationLayer()
    meta = MetaCognitionLayer()

    last = {}
    for b in bars:
        out = p.process(b, ctx); ctx.record(out)
        sd = s.process(out.payload, ctx); ctx.record(sd)
        pr = pa.process(sd.payload, ctx); ctx.record(pr)
        m = mem.process(pr.payload, ctx); ctx.record(m)
        td = temp.process([], ctx); ctx.record(td)
        dp = decep.process(pr.payload, ctx); ctx.record(dp)
        rg = reg.process(pr.payload, ctx); ctx.record(rg)
        mc = meta.process({}, ctx); ctx.record(mc)
        last = dict(ctx.upstream_outputs)
        ctx.upstream_outputs.clear()
    return last


def test_all_layers_emit_outputs(synthetic_bars, ctx):
    last = _run_through(synthetic_bars, ctx)
    assert LayerName.PRIMITIVES in last
    assert LayerName.STRUCTURAL in last
    assert LayerName.PATHOLOGY in last
    assert LayerName.MEMORY in last
    assert LayerName.TEMPORAL in last
    assert LayerName.DECEPTION in last
    assert LayerName.REGIME in last
    assert LayerName.META in last


def test_layer_outputs_are_immutable(synthetic_bars, ctx):
    last = _run_through(synthetic_bars, ctx)
    out = last[LayerName.STRUCTURAL]
    try:
        out.confidence = 0.0  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised, "LayerOutput must be frozen"


def test_confidence_in_unit_interval(synthetic_bars, ctx):
    last = _run_through(synthetic_bars, ctx)
    for out in last.values():
        assert 0.0 <= out.confidence <= 1.0
