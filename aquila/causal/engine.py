from __future__ import annotations

from aquila.causal.schemas import CausalEdge, CausalEdgeKind, CausalGraph
from aquila.core.base import LayerOutput
from aquila.core.types import LayerName


class CausalGraphEngine:
    """Builds an event-level causal graph for a single cycle.

    Edges are derived from the explicit DAG + each `LayerOutput.evidence`
    list. This is a *deterministic, transparent* causal mapping — no
    learned causality.
    """

    DAG_EDGES: tuple[tuple[LayerName, LayerName, CausalEdgeKind], ...] = (
        (LayerName.PRIMITIVES, LayerName.STRUCTURAL, CausalEdgeKind.STRUCTURAL_DEPENDENCY),
        (LayerName.STRUCTURAL, LayerName.PATHOLOGY, CausalEdgeKind.STRUCTURAL_DEPENDENCY),
        (LayerName.PATHOLOGY, LayerName.MEMORY, CausalEdgeKind.STRUCTURAL_DEPENDENCY),
        (LayerName.PATHOLOGY, LayerName.DECEPTION, CausalEdgeKind.CAUSAL_ESCALATION),
        (LayerName.PATHOLOGY, LayerName.REGIME, CausalEdgeKind.TEMPORAL_CAUSAL),
        (LayerName.STRUCTURAL, LayerName.TEMPORAL, CausalEdgeKind.CORRELATION),
        (LayerName.PATHOLOGY, LayerName.META, CausalEdgeKind.CAUSAL_ESCALATION),
        (LayerName.MEMORY, LayerName.META, CausalEdgeKind.CORRELATION),
        (LayerName.DECEPTION, LayerName.META, CausalEdgeKind.CAUSAL_ESCALATION),
        (LayerName.REGIME, LayerName.META, CausalEdgeKind.TEMPORAL_CAUSAL),
        (LayerName.TEMPORAL, LayerName.META, CausalEdgeKind.CORRELATION),
    )

    def build(self, outputs: dict[LayerName, LayerOutput]) -> CausalGraph:
        edges: list[CausalEdge] = []
        for src, dst, kind in self.DAG_EDGES:
            s = outputs.get(src)
            d = outputs.get(dst)
            if s and d:
                edges.append(CausalEdge(
                    from_event=s.event_id, to_event=d.event_id,
                    kind=kind, weight=s.confidence,
                    rationale=f"{src.value}->{dst.value}",
                ))
        for ln, o in outputs.items():
            for ref in o.evidence:
                edges.append(CausalEdge(
                    from_event=ref.event_id, to_event=o.event_id,
                    kind=CausalEdgeKind.STRUCTURAL_DEPENDENCY,
                    weight=o.confidence, rationale="explicit_evidence",
                ))
        return CausalGraph(edges=edges)
