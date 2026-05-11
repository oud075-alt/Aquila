"""Acceptance failure model.

After a breakout or expansion the market should *accept* the new price
range — bars should close inside the new value area and revisits should
hold. Acceptance failure means price keeps reverting back into the prior
range or rejects the new level repeatedly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import clamp, linear_regression, safe_div
from brain.schemas import ActualBehaviorProfile, Candle, ExpectationProfile


@dataclass
class AcceptanceAssessment:
    score: float
    features: Dict[str, float]


class AcceptanceFailureModel:
    def __init__(self, lookback: int = 80):
        self.lookback = lookback

    def evaluate(
        self,
        candles: List[Candle],
        expected: ExpectationProfile,
        actual: ActualBehaviorProfile,
    ) -> AcceptanceAssessment:
        if len(candles) < self.lookback + 10:
            return AcceptanceAssessment(0.0, {})

        recent = candles[-self.lookback :]
        closes = np.array([c.close for c in recent], dtype=np.float64)

        # Identify the most recent significant breakout level: highest high
        # / lowest low of the first half of lookback.
        half = self.lookback // 2
        prior_high = float(np.max(closes[:half]))
        prior_low = float(np.min(closes[:half]))

        post = closes[half:]
        breakouts_up = int(np.sum(post > prior_high))
        breakouts_dn = int(np.sum(post < prior_low))
        reverts_up = int(np.sum(np.diff(post > prior_high).astype(int) == -1))
        reverts_dn = int(np.sum(np.diff(post < prior_low).astype(int) == -1))

        # Acceptance ratio: time spent beyond breakout level
        time_above = float(safe_div(breakouts_up, post.size, 0.0))
        time_below = float(safe_div(breakouts_dn, post.size, 0.0))
        time_outside = max(time_above, time_below)

        # Whipsaw count: reversion frequency
        whipsaws = reverts_up + reverts_dn
        whipsaw_rate = float(safe_div(whipsaws, post.size, 0.0))

        acceptance_deficit = max(0.0, expected.expected_acceptance - actual.realized_acceptance)
        acceptance_deficit_norm = clamp(
            safe_div(acceptance_deficit, expected.expected_acceptance + 0.1, 0.0),
            0.0,
            1.0,
        )

        score = clamp(
            0.40 * acceptance_deficit_norm
            + 0.35 * (1.0 - time_outside)
            + 0.25 * whipsaw_rate,
            0.0,
            1.0,
        )

        return AcceptanceAssessment(
            score=score,
            features={
                "time_outside": float(time_outside),
                "whipsaw_rate": float(whipsaw_rate),
                "acceptance_deficit": float(acceptance_deficit_norm),
                "breakouts_up": float(breakouts_up),
                "breakouts_dn": float(breakouts_dn),
            },
        )
