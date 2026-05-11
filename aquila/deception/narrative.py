"""Narrative divergence — measures inconsistency between stated structural
'story' (e.g. trend) and microstructural evidence (e.g. weak body, wick).
"""

from __future__ import annotations

from aquila.core.numeric import safe_prob
from aquila.deception.schemas import NarrativeDivergence
from aquila.pathology.schemas import PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis, StructuralState


def narrative_divergence(
    structural: StructuralDiagnosis,
    pathology: PathologyReport,
    primitives: PrimitiveSnapshot | None,
) -> NarrativeDivergence:
    score = 0.0
    parts: list[str] = []
    if primitives is None:
        return NarrativeDivergence(score=0.0, description="no_microstructure")

    if structural.state in (StructuralState.TREND_UP, StructuralState.TREND_DOWN):
        if primitives.body_ratio < 0.4:
            score += 0.3
            parts.append("trend with weak body")
        if max(primitives.upper_wick_ratio, primitives.lower_wick_ratio) > 0.5:
            score += 0.25
            parts.append("trend with rejection wick")
    if pathology.aggregate_contradiction_score > 0.5:
        score += 0.3
        parts.append("high pathology contradiction")

    return NarrativeDivergence(
        score=safe_prob(score),
        description="; ".join(parts) if parts else "coherent narrative",
    )
