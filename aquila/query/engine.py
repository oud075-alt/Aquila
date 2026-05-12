from __future__ import annotations

from aquila.causal.engine import LineageGraph
from aquila.core.base import LayerOutput
from aquila.core.types import LayerName
from aquila.governance.eventstore import EventStore
from aquila.query.projections import Projection
from aquila.query.schemas import (
    CausalTraceQuery,
    CausalTraceResult,
    PathologyHistoryQuery,
    PathologyHistoryResult,
    StructuralStateQuery,
    StructuralStateResult,
    TemporalContradictionQuery,
    TemporalContradictionResult,
)


class CognitiveQueryEngine:
    def __init__(self, store: EventStore, latest: dict | None = None) -> None:
        self._store = store
        self._proj = Projection()
        self._proj.ingest(store.stream())
        self._latest_per_corr: dict[str, dict[LayerName, LayerOutput]] = latest or {}

    def refresh(self) -> None:
        self._proj = Projection()
        self._proj.ingest(self._store.stream())

    def structural_states(self, q: StructuralStateQuery) -> StructuralStateResult:
        return StructuralStateResult(states=self._proj.structural_states(q.symbol, q.last_n))

    def pathology_history(self, q: PathologyHistoryQuery) -> PathologyHistoryResult:
        ps, cs = self._proj.pathology_history(q.symbol, q.last_n)
        return PathologyHistoryResult(pathology_scores=ps, contradiction_scores=cs)

    def temporal_contradictions(self, q: TemporalContradictionQuery) -> TemporalContradictionResult:
        evs = [e for e in self._store.stream() if e.symbol == q.symbol and e.layer == LayerName.TEMPORAL]
        edges = []
        for e in evs[-5:]:
            edges.extend(e.payload.get("conflict_graph", {}).get("edges", []))
        return TemporalContradictionResult(edges=edges)

    def causal_trace(self, q: CausalTraceQuery) -> CausalTraceResult:
        outs = self._latest_per_corr.get(q.correlation_id)
        if not outs:
            evs = self._proj.by_correlation(q.correlation_id)
            return CausalTraceResult(nodes=[e.event_id for e in evs], edges=[])
        graph = LineageGraph().build(outs)
        return CausalTraceResult(
            nodes=[o.event_id for o in outs.values()],
            edges=[e.model_dump() for e in graph.edges],
        )
