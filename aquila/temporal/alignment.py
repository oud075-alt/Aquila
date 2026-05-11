"""Alignment scoring — how unanimous are the timeframes?"""

from __future__ import annotations

from collections import Counter

from aquila.core.numeric import safe_prob
from aquila.structural.schemas import StructuralState
from aquila.temporal.schemas import HierarchyWeights, TimeframeState

# Direction classes for "do we agree" semantics
_DIRECTIONAL = {
    StructuralState.TREND_UP: 1,
    StructuralState.TREND_DOWN: -1,
    StructuralState.DISPLACEMENT: 0,
    StructuralState.EXPANSION: 0,
    StructuralState.COMPRESSION: 0,
    StructuralState.RANGE: 0,
    StructuralState.EXHAUSTION: 0,
    StructuralState.ABSORPTION: 0,
    StructuralState.UNKNOWN: 0,
}


def alignment_score(states: list[TimeframeState], weights: HierarchyWeights) -> float:
    if not states:
        return 0.0
    total_w = 0.0
    score = 0.0
    counter: Counter[StructuralState] = Counter()
    for s in states:
        w = weights.weight(s.timeframe)
        total_w += w
        counter[s.state] += 1
    if total_w == 0.0:
        return 0.0
    dominant_state, dominant_count = counter.most_common(1)[0]
    for s in states:
        w = weights.weight(s.timeframe)
        if s.state == dominant_state:
            score += w
    return safe_prob(score / total_w)
