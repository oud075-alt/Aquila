"""Layer 5 engine — Temporal Hierarchy Cognition."""

from __future__ import annotations

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.time import Timeframe
from aquila.core.types import LayerName
from aquila.temporal.alignment import alignment_score
from aquila.temporal.conflict_graph import build_conflict_graph
from aquila.temporal.fusion import fuse_states
from aquila.temporal.interfaces import TemporalReasoningService
from aquila.temporal.schemas import (
    HierarchyWeights,
    TemporalCognition,
    TimeframeState,
)


class TemporalHierarchyLayer(TemporalReasoningService):
    layer_name = LayerName.TEMPORAL

    def __init__(self, weights: HierarchyWeights | None = None) -> None:
        super().__init__()
        self._states: dict[Timeframe, TimeframeState] = {}
        self._weights = weights or HierarchyWeights()

    def update_timeframe(self, state: TimeframeState) -> None:
        self._states[state.timeframe] = state

    def process(self, payload: list, ctx: LayerContext) -> LayerOutput[TemporalCognition]:
        # payload may be a list of TimeframeState; if empty, use cached states
        for s in payload or []:
            if isinstance(s, TimeframeState):
                self.update_timeframe(s)

        states = list(self._states.values())
        if not states:
            cog = TemporalCognition(
                states=[],
                fused_state=__import__("aquila.structural.schemas", fromlist=["StructuralState"]).StructuralState.UNKNOWN,
                alignment_score=0.0,
                conflict_graph=build_conflict_graph([]),
                weights=self._weights,
            )
            return self.wrap(payload=cog, ctx=ctx, confidence=0.0, visibility="blind")

        graph = build_conflict_graph(states)
        align = alignment_score(states, self._weights)
        fused = fuse_states(states, self._weights)
        cog = TemporalCognition(
            states=states,
            fused_state=fused,
            alignment_score=align,
            conflict_graph=graph,
            weights=self._weights,
        )
        confidence = max(0.0, align - graph.aggregate_conflict * 0.5)
        visibility = "full" if len(states) >= 3 else "partial"
        return self.wrap(payload=cog, ctx=ctx, confidence=confidence, visibility=visibility)
