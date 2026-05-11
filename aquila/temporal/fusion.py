"""State fusion across timeframes."""

from __future__ import annotations

from collections import defaultdict

from aquila.structural.schemas import StructuralState
from aquila.temporal.schemas import HierarchyWeights, TimeframeState


def fuse_states(
    states: list[TimeframeState], weights: HierarchyWeights
) -> StructuralState:
    if not states:
        return StructuralState.UNKNOWN
    score: dict[StructuralState, float] = defaultdict(float)
    for s in states:
        w = weights.weight(s.timeframe) * max(0.01, s.confidence)
        score[s.state] += w
    return max(score.items(), key=lambda kv: kv[1])[0]
