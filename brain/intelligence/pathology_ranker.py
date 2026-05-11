"""Pathology ranker.

Provides a deterministic, priority-ordered ranking of the active pathology
signals so the diagnostic report can highlight the dominant contributors.

Implements DIAGNOSTIC PRIORITY HIERARCHY:
1. Structural instability
2. Stress escalation
3. Contradiction severity
4. Liquidity fragility
5. Continuation quality
6. Volatility behaviour
7. Trend appearance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from brain.schemas import ContradictionScores, PathologyScores


_PRIORITY_ORDER: List[Tuple[str, float]] = [
    ("structural_instability", 1.00),
    ("stress_escalation", 0.95),
    ("contradiction_severity", 0.90),
    ("liquidity_fragility", 0.85),
    ("continuation_failure", 0.80),
    ("pre_collapse", 0.78),
    ("compression_pressure", 0.70),
    ("hidden_exhaustion", 0.65),
    ("behavioral_divergence", 0.62),
    ("manipulation_footprint", 0.60),
    ("acceptance_failure", 0.58),
    ("entropy_disorder", 0.55),
]


@dataclass
class RankedPathology:
    name: str
    score: float
    priority_weight: float
    weighted_score: float


class PathologyRanker:
    def rank(
        self,
        pathology: PathologyScores,
        contradiction: ContradictionScores,
    ) -> List[RankedPathology]:
        pd = pathology.as_dict()
        cd = contradiction.as_dict()
        contradiction_severity = max(cd.values()) if cd else 0.0
        merged = {**pd, "contradiction_severity": contradiction_severity}

        ranked: List[RankedPathology] = []
        for name, weight in _PRIORITY_ORDER:
            score = float(merged.get(name, 0.0))
            ranked.append(
                RankedPathology(
                    name=name,
                    score=score,
                    priority_weight=weight,
                    weighted_score=score * weight,
                )
            )
        ranked.sort(key=lambda r: r.weighted_score, reverse=True)
        return ranked
