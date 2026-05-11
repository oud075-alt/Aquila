"""Pre-collapse pathology model.

Pre-collapse is a fusion model that combines:

* hidden exhaustion (momentum dying while price extends)
* liquidity fragility (vacuum + sweep risk)
* stress escalation (rising vol-of-vol + rejections)
* acceptance failure (failed continuation post-expansion)
* behavioural divergence (price–delta–RSI disagreement)
* low directional efficiency (high entropy / low coherence)

It models the system-wide probability that price is about to fail and
collapse rather than continue expanding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from brain.math_core import clamp, probability_or


@dataclass
class PreCollapseAssessment:
    score: float
    direction: str  # "DOWNSIDE" | "UPSIDE_RELEASE" | "NEUTRAL"
    features: Dict[str, float]


class PreCollapseModel:
    """Composite pathology requiring multiple confirmations."""

    def __init__(self,
                 weight_exhaustion: float = 0.20,
                 weight_liquidity: float = 0.18,
                 weight_stress: float = 0.20,
                 weight_acceptance: float = 0.16,
                 weight_divergence: float = 0.14,
                 weight_instability: float = 0.12):
        self.weights = {
            "exhaustion": weight_exhaustion,
            "liquidity": weight_liquidity,
            "stress": weight_stress,
            "acceptance": weight_acceptance,
            "divergence": weight_divergence,
            "instability": weight_instability,
        }

    def evaluate(
        self,
        exhaustion: float,
        liquidity_fragility: float,
        stress: float,
        acceptance_failure: float,
        divergence: float,
        instability: float,
        bull_bias: float = 0.0,
    ) -> PreCollapseAssessment:
        components = {
            "exhaustion": clamp(exhaustion, 0.0, 1.0),
            "liquidity": clamp(liquidity_fragility, 0.0, 1.0),
            "stress": clamp(stress, 0.0, 1.0),
            "acceptance": clamp(acceptance_failure, 0.0, 1.0),
            "divergence": clamp(divergence, 0.0, 1.0),
            "instability": clamp(instability, 0.0, 1.0),
        }

        # Weighted sum constrained to [0,1]
        weighted = sum(self.weights[k] * v for k, v in components.items())
        # Reinforced by probability-OR fusion (so a single very high signal
        # still produces a high score).
        fused = probability_or(list(components.values()))
        score = clamp(0.55 * weighted + 0.45 * fused, 0.0, 1.0)

        # Direction inference. If exhaustion + divergence dominate and the
        # market has positive bias, lean DOWNSIDE; if compression-pressure
        # context drives, it could be release.
        direction = "NEUTRAL"
        if score >= 0.5:
            if bull_bias > 0.0 and components["exhaustion"] > 0.5:
                direction = "DOWNSIDE"
            elif bull_bias < 0.0 and components["exhaustion"] > 0.5:
                direction = "UPSIDE_RELEASE"
            elif components["stress"] > 0.6:
                direction = "DOWNSIDE"
            else:
                direction = "NEUTRAL"

        return PreCollapseAssessment(score=score, direction=direction, features=components)
