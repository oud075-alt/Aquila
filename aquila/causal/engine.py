"""Per-cycle event lineage graph (legacy module name retained).

The engine that was previously called ``CausalGraphEngine`` builds a
graph over the event ids of the layer outputs in a single cycle. The
edges come from two sources only:

1. A static, hand-written list of layer-to-layer adjacencies that
   describes the cognitive pipeline DAG (``DAG_EDGES``).
2. The explicit ``LayerOutput.evidence`` citations attached by each
   layer.

There is no statistical causal inference. There is no do-calculus.
There is no learned graph. The output is a lineage graph: which
upstream output was cited by which downstream output. Calling it
"causal" was a name-trap. See ``docs/adr/ADR-0009-rename-causal-graph-engine.md``.

Public surface:

- ``LineageGraph`` — the honest name.
- ``CausalGraphEngine`` — deprecation alias. Emits ``DeprecationWarning``
  on every attribute access. Will be removed two PRs after the rename
  per HARD RULE #8.
"""

from __future__ import annotations

import warnings

from aquila.causal.schemas import CausalEdge, CausalEdgeKind, CausalGraph
from aquila.core.base import LayerOutput
from aquila.core.types import LayerName


class LineageGraph:
    """Builds an event-level lineage graph for a single cycle.

    Edges come from the explicit pipeline DAG plus each
    ``LayerOutput.evidence`` list. The graph is deterministic and
    transparent; it carries no claim of statistical causality.
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


class _DeprecatedCausalGraphEngineMeta(type):
    """Emit ``DeprecationWarning`` on every access of the legacy class."""

    def __getattribute__(cls, item):
        if item not in {"__class__", "__name__", "__qualname__", "__mro__"}:
            warnings.warn(
                "CausalGraphEngine is deprecated; use LineageGraph. "
                "The legacy name will be removed two PRs after the rename "
                "(see ADR-0009).",
                DeprecationWarning,
                stacklevel=2,
            )
        return super().__getattribute__(item)


class CausalGraphEngine(LineageGraph, metaclass=_DeprecatedCausalGraphEngineMeta):
    """Deprecated alias for :class:`LineageGraph`.

    Kept per HARD RULE #8. Do not extend or add behaviour here.
    """

    pass
