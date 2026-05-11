"""Structural instability model.

Measures the disorder of price structure using entropy of returns, vol-
of-vol, directional incoherence and rolling std spikes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import (
    clamp,
    directional_coherence,
    rolling_std,
    safe_array,
    shannon_entropy,
)
from brain.schemas import Candle


@dataclass
class InstabilityAssessment:
    score: float
    features: Dict[str, float]


class StructuralInstabilityModel:
    def __init__(self, window: int = 100):
        self.window = window

    def evaluate(self, candles: List[Candle]) -> InstabilityAssessment:
        if len(candles) < self.window + 2:
            return InstabilityAssessment(0.0, {})

        closes = np.array([c.close for c in candles[-self.window :]], dtype=np.float64)
        log_rets = np.diff(np.log(np.maximum(closes, 1e-12)))

        entropy = shannon_entropy(log_rets, bins=20)
        coherence = directional_coherence(log_rets)
        incoherence = clamp(1.0 - coherence, 0.0, 1.0)

        # Vol-of-vol: rolling std of rolling std
        roll_std = rolling_std(log_rets, window=20)
        if roll_std.size > 3:
            base = float(np.median(roll_std)) or 1e-9
            vov = float(np.std(roll_std[-20:], ddof=1)) / base
        else:
            vov = 0.0
        vov_norm = clamp(vov, 0.0, 1.0)

        # Range-of-range disorder
        ranges = np.array([c.range for c in candles[-self.window :]], dtype=np.float64)
        rng_std = float(np.std(ranges, ddof=1)) if ranges.size > 2 else 0.0
        rng_mean = float(np.mean(ranges)) or 1e-9
        rng_disorder = clamp(rng_std / rng_mean - 0.5, 0.0, 1.0)

        # Sign reversal density
        signs = np.sign(log_rets)
        flips = float(np.mean(signs[1:] != signs[:-1]))
        flip_excess = clamp(flips - 0.5, 0.0, 0.5) * 2.0

        score = clamp(
            0.30 * entropy
            + 0.25 * incoherence
            + 0.20 * vov_norm
            + 0.15 * rng_disorder
            + 0.10 * flip_excess,
            0.0,
            1.0,
        )

        return InstabilityAssessment(
            score=score,
            features={
                "entropy": float(entropy),
                "coherence": float(coherence),
                "vol_of_vol": float(vov_norm),
                "range_disorder": float(rng_disorder),
                "flip_excess": float(flip_excess),
            },
        )
