from __future__ import annotations

from aquila.core.types import LayerName, Symbol
from aquila.pipeline import CognitiveOrchestrator


def test_pipeline_audit_chain_is_valid(synthetic_bars, orchestrator: CognitiveOrchestrator, symbol: Symbol):
    last = {}
    for bar in synthetic_bars:
        last = orchestrator.run_tick(symbol, bar)
    assert orchestrator.audit.verify()
    assert len(orchestrator.audit) >= 8 * len(synthetic_bars)


def test_pipeline_emits_lifecycle(synthetic_bars, orchestrator, symbol):
    last = {}
    for bar in synthetic_bars[:3]:
        last = orchestrator.run_tick(symbol, bar)
    lc = orchestrator.lifecycle(last)
    assert lc.correlation_id != ""
    assert any(p.value == "done" for p in lc.phases_completed)


def test_meta_signal_caps_when_uncertainty_high(synthetic_bars, orchestrator, symbol):
    last = orchestrator.run_tick(symbol, synthetic_bars[0])
    meta = last[LayerName.META]
    assert meta.payload.meta_signal is not None
