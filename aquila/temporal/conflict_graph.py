"""Cross-timeframe contradiction graph."""

from __future__ import annotations

from aquila.core.time import Timeframe
from aquila.structural.schemas import StructuralState
from aquila.temporal.alignment import _DIRECTIONAL
from aquila.temporal.schemas import TemporalConflict, TemporalConflictGraph, TimeframeState


def build_conflict_graph(states: list[TimeframeState]) -> TemporalConflictGraph:
    by_tf: dict[Timeframe, TimeframeState] = {s.timeframe: s for s in states}
    ordered = sorted(by_tf.values(), key=lambda s: s.timeframe.minutes)
    edges: list[TemporalConflict] = []
    for i, lower in enumerate(ordered):
        for higher in ordered[i + 1 :]:
            la = _DIRECTIONAL[lower.state]
            ha = _DIRECTIONAL[higher.state]
            if la == 0 or ha == 0:
                if lower.state != higher.state:
                    edges.append(TemporalConflict(
                        higher=higher.timeframe, lower=lower.timeframe,
                        higher_state=higher.state, lower_state=lower.state,
                        score=0.3, rationale="state mismatch (non-directional)",
                    ))
            elif la != ha:
                edges.append(TemporalConflict(
                    higher=higher.timeframe, lower=lower.timeframe,
                    higher_state=higher.state, lower_state=lower.state,
                    score=0.8, rationale="opposing directional bias",
                ))
    return TemporalConflictGraph(edges=edges)
