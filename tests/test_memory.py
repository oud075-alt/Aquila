from __future__ import annotations

import tempfile
from pathlib import Path

from aquila.core.base import LayerContext
from aquila.core.types import LayerName, Symbol
from aquila.memory import EpisodicMemoryLayer, JsonlStore
from aquila.pathology import PathologyContradictionLayer
from aquila.primitives import PrimitiveMetricsLayer
from aquila.structural import StructuralDiagnosisLayer


def test_jsonl_store_roundtrip(synthetic_bars, symbol):
    with tempfile.TemporaryDirectory() as d:
        store = JsonlStore(Path(d) / "mem.jsonl")
        mem = EpisodicMemoryLayer(store=store)
        p = PrimitiveMetricsLayer(window=20)
        s = StructuralDiagnosisLayer()
        pa = PathologyContradictionLayer()
        for b in synthetic_bars[:40]:
            ctx = LayerContext(correlation_id="c", symbol=symbol)
            po = p.process(b, ctx); ctx.record(po)
            so = s.process(po.payload, ctx); ctx.record(so)
            pao = pa.process(so.payload, ctx); ctx.record(pao)
            mem.process(pao.payload, ctx)
        assert store.size() > 0
        loaded = list(store.all())
        assert len(loaded) == store.size()


def test_synthetic_origin_does_not_write_real_archive(synthetic_bars, symbol):
    mem = EpisodicMemoryLayer()
    p = PrimitiveMetricsLayer(window=20)
    s = StructuralDiagnosisLayer()
    pa = PathologyContradictionLayer()
    for b in synthetic_bars[:10]:
        ctx = LayerContext(correlation_id="c", symbol=symbol, origin="synthetic")
        po = p.process(b, ctx); ctx.record(po)
        so = s.process(po.payload, ctx); ctx.record(so)
        pao = pa.process(so.payload, ctx); ctx.record(pao)
        out = mem.process(pao.payload, ctx)
        assert out.payload.written is False
    assert mem.archive.size() == 0
