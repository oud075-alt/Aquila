"""Confidence engine.

Estimates how reliable the current diagnosis is. Returns a
:class:`ConfidenceScores` instance that captures sample size adequacy,
signal-to-noise ratio, internal consistency of contradiction signals,
and noise contamination.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from brain.math_core import clamp
from brain.schemas import (
    ActualBehaviorProfile,
    Candle,
    ConfidenceScores,
    ContradictionScores,
    ExpectationProfile,
    PathologyScores,
)
from config import get_market_config


class ConfidenceEngine:
    def __init__(self):
        self.cfg = get_market_config()

    def evaluate(
        self,
        candles: List[Candle],
        expected: ExpectationProfile,
        actual: ActualBehaviorProfile,
        pathology: PathologyScores,
        contradiction: ContradictionScores,
    ) -> ConfidenceScores:
        n = len(candles)
        sample_score = clamp(n / max(self.cfg.confidence_minimum_samples, 1), 0.0, 1.0)

        # Signal quality: how strongly any pathology stands out from noise.
        scores = list(pathology.as_dict().values())
        max_p = max(scores) if scores else 0.0
        mean_p = float(np.mean(scores)) if scores else 0.0
        signal_quality = clamp((max_p - mean_p) * 2.0, 0.0, 1.0)

        # Contradiction consistency: how aligned the individual contradiction
        # signals are (low variance amongst contradicting features = consistent).
        cd_values = list(contradiction.as_dict().values())
        if cd_values:
            var = float(np.var(cd_values))
            consistency = clamp(1.0 - var * 4.0, 0.0, 1.0)
        else:
            consistency = 1.0

        # Noise score: entropy of returns + wick/body ratio
        entropy = float(actual.metadata.get("entropy", 0.0))
        wick = float(actual.wick_body_ratio)
        noise = clamp(0.5 * entropy + 0.5 * clamp(wick / 4.0, 0.0, 1.0), 0.0, 1.0)
        noise_score = clamp(1.0 - noise, 0.0, 1.0)

        overall = clamp(
            0.30 * sample_score
            + 0.30 * signal_quality
            + 0.20 * consistency
            + 0.20 * noise_score,
            0.0,
            1.0,
        )

        return ConfidenceScores(
            sample_size_score=sample_score,
            signal_quality_score=signal_quality,
            contradiction_consistency=consistency,
            noise_score=noise_score,
            overall_confidence=overall,
        )
