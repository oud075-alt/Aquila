"""Continuation failure model.

Detects breakouts / expansions that should continue (per expectation) but
fail. Compares actual follow-through and persistence with expected and
measures the relative deficit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import clamp, safe_div
from brain.schemas import ActualBehaviorProfile, Candle, ExpectationProfile


@dataclass
class ContinuationFailureAssessment:
    score: float
    failed_breakouts: int
    features: Dict[str, float]


class ContinuationFailureModel:
    def __init__(self, lookback: int = 60, breakout_z: float = 1.5):
        self.lookback = lookback
        self.breakout_z = breakout_z

    def evaluate(
        self,
        candles: List[Candle],
        expected: ExpectationProfile,
        actual: ActualBehaviorProfile,
    ) -> ContinuationFailureAssessment:
        if len(candles) < self.lookback + 10:
            return ContinuationFailureAssessment(0.0, 0, {})

        closes = np.array([c.close for c in candles[-self.lookback :]], dtype=np.float64)
        log_rets = np.diff(np.log(np.maximum(closes, 1e-12)))
        mu = float(np.mean(log_rets))
        sigma = float(np.std(log_rets, ddof=1)) or 1e-9
        z = (log_rets - mu) / sigma
        breakout_idx = np.where(np.abs(z) > self.breakout_z)[0]

        failed = 0
        analysed = 0
        for i in breakout_idx:
            if i + 5 >= log_rets.size:
                continue
            analysed += 1
            direction = np.sign(log_rets[i])
            future_dir = log_rets[i + 1 : i + 6]
            same_dir_run = 0
            for v in future_dir:
                if np.sign(v) == direction:
                    same_dir_run += 1
                else:
                    break
            if same_dir_run <= 1:
                failed += 1
        fail_rate = float(safe_div(failed, max(1, analysed), default=0.0))

        followthrough_gap = max(0.0, expected.expected_breakout_followthrough - actual.realized_breakout_followthrough)
        persistence_gap = max(0.0, expected.expected_continuation_persistence - actual.realized_continuation_persistence)

        score = clamp(
            0.50 * fail_rate
            + 0.30 * clamp(followthrough_gap / max(expected.expected_breakout_followthrough, 0.1), 0.0, 1.0)
            + 0.20 * clamp(persistence_gap / max(expected.expected_continuation_persistence, 0.1), 0.0, 1.0),
            0.0,
            1.0,
        )

        return ContinuationFailureAssessment(
            score=score,
            failed_breakouts=int(failed),
            features={
                "analysed_breakouts": float(analysed),
                "fail_rate": float(fail_rate),
                "followthrough_gap": float(followthrough_gap),
                "persistence_gap": float(persistence_gap),
            },
        )
