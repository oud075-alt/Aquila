"""Contradiction engine.

Combines :class:`ExpectationProfile`, :class:`ActualBehaviorProfile` and
the anomaly detector probabilities into a single
:class:`ContradictionScores` structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from brain.math_core import clamp
from brain.pathology.anomaly_detector import AnomalyDetector, AnomalyResult
from brain.schemas import (
    ActualBehaviorProfile,
    ContradictionScores,
    ExpectationProfile,
)
from config import get_market_config


@dataclass
class ContradictionAnalysis:
    scores: ContradictionScores
    anomaly: AnomalyResult
    aggregate: float
    reasoning: List[str]


class ContradictionEngine:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.weights = get_market_config().contradiction_weights

    def evaluate(
        self,
        expected: ExpectationProfile,
        actual: ActualBehaviorProfile,
    ) -> ContradictionAnalysis:
        anomaly = self.detector.evaluate(expected, actual)
        p = anomaly.probabilities

        scores = ContradictionScores(
            momentum_vs_price=clamp(
                self.weights.momentum_vs_price * 0.5 * (p["persistence"] + p["slope"]),
                0.0, 1.0,
            ),
            volume_vs_price=clamp(
                self.weights.volume_vs_price * p["participation"],
                0.0, 1.0,
            ),
            volatility_vs_continuation=clamp(
                self.weights.volatility_vs_continuation
                * 0.5 * (p["volatility"] + p["followthrough"]),
                0.0, 1.0,
            ),
            range_vs_acceptance=clamp(
                self.weights.range_vs_acceptance
                * 0.5 * (p["atr"] + p["acceptance"]),
                0.0, 1.0,
            ),
            breadth_vs_expansion=clamp(
                self.weights.breadth_vs_expansion
                * 0.5 * (p["participation"] + p["compression_release"]),
                0.0, 1.0,
            ),
            liquidity_vs_move=clamp(
                self.weights.liquidity_vs_move
                * 0.5 * (p["participation"] + p["atr"]),
                0.0, 1.0,
            ),
            wick_vs_body=clamp(actual.wick_body_ratio / 4.0, 0.0, 1.0),
            entropy_vs_direction=clamp(
                self.weights.entropy_vs_direction
                * float(actual.metadata.get("entropy", 0.0))
                * (1.0 - float(actual.metadata.get("directional_coherence", 0.0))),
                0.0, 1.0,
            ),
        )

        reasoning: List[str] = []
        if scores.momentum_vs_price > 0.55:
            reasoning.append(
                "Momentum is materially weaker than the regime's healthy momentum "
                "expectation — price extension lacks underlying persistence."
            )
        if scores.volume_vs_price > 0.55:
            reasoning.append(
                "Participation is deficient relative to the move size: price action "
                "is occurring without proportionate volume confirmation."
            )
        if scores.volatility_vs_continuation > 0.55:
            reasoning.append(
                "Volatility regime contradicts continuation: realised vol is far "
                "from expectation while follow-through is decaying."
            )
        if scores.range_vs_acceptance > 0.55:
            reasoning.append(
                "Range expansion is not being accepted — closes keep returning to "
                "the prior value area."
            )
        if scores.liquidity_vs_move > 0.55:
            reasoning.append(
                "Liquidity does not justify the move — thin participation suggests "
                "displacement rather than genuine repricing."
            )
        if scores.entropy_vs_direction > 0.55:
            reasoning.append(
                "Directional coherence is decaying while entropy rises — structure "
                "is losing internal organisation."
            )
        if not reasoning:
            reasoning.append(
                "No dominant contradiction detected: expectation and observation "
                "remain aligned within tolerance."
            )

        aggregate = clamp(
            sum(scores.as_dict().values()) / max(1, len(scores.as_dict())),
            0.0, 1.0,
        )
        return ContradictionAnalysis(scores=scores, anomaly=anomaly, aggregate=aggregate, reasoning=reasoning)
