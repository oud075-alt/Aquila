"""Migration tests for the CausalGraphEngine → LineageGraph rename (M3.2)."""

from __future__ import annotations

import warnings

import pytest

from aquila.causal import CausalGraphEngine, LineageGraph


def test_new_name_exists_and_builds(orchestrator, symbol, synthetic_bars):
    last = {}
    for b in synthetic_bars[:5]:
        last = orchestrator.run_tick(symbol, b)
    graph = LineageGraph().build(last)
    assert len(graph.edges) > 0
    for edge in graph.edges:
        assert edge.from_event
        assert edge.to_event
        assert edge.weight >= 0.0


def test_legacy_name_still_importable():
    assert CausalGraphEngine is not None


def test_legacy_name_emits_deprecation_warning_on_access():
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        _ = CausalGraphEngine.DAG_EDGES
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "CausalGraphEngine is deprecated" in str(w.message)
        for w in records
    ), f"expected DeprecationWarning, got: {[str(w.message) for w in records]}"


def test_legacy_subclass_produces_same_graph(orchestrator, symbol, synthetic_bars):
    last = {}
    for b in synthetic_bars[:3]:
        last = orchestrator.run_tick(symbol, b)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        legacy_graph = CausalGraphEngine().build(last)
    new_graph = LineageGraph().build(last)
    assert len(new_graph.edges) == len(legacy_graph.edges)


def test_query_engine_uses_new_class(orchestrator, symbol, synthetic_bars):
    """End-to-end smoke: the query engine path that used to call
    CausalGraphEngine still returns a non-empty trace under the new
    name."""
    from aquila.governance.eventstore import EventStore
    from aquila.query.engine import CognitiveQueryEngine
    from aquila.query.schemas import CausalTraceQuery

    es = EventStore()
    latest = {}
    for b in synthetic_bars[:3]:
        last = orchestrator.run_tick(symbol, b)
        for o in last.values():
            es.append(o)
        latest[next(iter(last.values())).correlation_id] = last
    corr = next(iter(latest.keys()))
    eng = CognitiveQueryEngine(es, latest)
    res = eng.causal_trace(CausalTraceQuery(correlation_id=corr))
    assert len(res.edges) > 0
