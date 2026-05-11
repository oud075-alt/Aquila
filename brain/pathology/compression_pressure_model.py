"""Compression-pressure model.

Measures the accumulation of pressure inside compressed structure: low
realised volatility, narrowing range, declining body share, increasing
volume accumulation despite shrinking range, and proximity to a long
duration of low BB-width.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import bollinger_width, clamp, linear_regression, safe_div
from brain.schemas import Candle


@dataclass
class CompressionAssessment:
    score: float
    duration: int
    release_probability: float
    features: Dict[str, float]


class CompressionPressureModel:
    def __init__(self, lookback: int = 80, period: int = 20):
        self.lookback = lookback
        self.period = period

    def evaluate(self, candles: List[Candle]) -> CompressionAssessment:
        if len(candles) < self.lookback + 5:
            return CompressionAssessment(0.0, 0, 0.0, {})

        closes = np.array([c.close for c in candles[-self.lookback :]], dtype=np.float64)
        ranges = np.array([c.range for c in candles[-self.lookback :]], dtype=np.float64)
        volumes = np.array([c.volume for c in candles[-self.lookback :]], dtype=np.float64)

        bbw = bollinger_width(closes, period=self.period, k=2.0)
        baseline = float(np.median(bbw)) or 1e-9
        latest = float(bbw[-1])
        compression_ratio = clamp(1.0 - latest / baseline, 0.0, 1.0)

        # Compression duration: bars in lowest 25 percentile of BBW
        q25 = float(np.quantile(bbw, 0.25))
        duration = int(np.sum(bbw[-self.period:] <= q25))

        # Range trend (negative slope = compressing)
        x = np.arange(ranges.size, dtype=np.float64)
        rng_slope, _, _ = linear_regression(x, ranges)
        rng_compress = clamp(-rng_slope / (np.mean(ranges) + 1e-9) * 30.0, 0.0, 1.0)

        # Volume accumulation despite compression
        vol_slope, _, _ = linear_regression(x, volumes)
        vol_accum = clamp(vol_slope / (np.mean(volumes) + 1e-9) * 30.0, 0.0, 1.0)

        pressure_score = clamp(
            0.45 * compression_ratio
            + 0.25 * rng_compress
            + 0.15 * vol_accum
            + 0.15 * clamp(duration / float(self.period), 0.0, 1.0),
            0.0,
            1.0,
        )

        # Release probability: rises with compression score and accumulated
        # duration; modulated by volume accumulation.
        release_prob = clamp(
            0.55 * pressure_score + 0.30 * (duration / float(self.period)) + 0.15 * vol_accum,
            0.0,
            1.0,
        )

        return CompressionAssessment(
            score=pressure_score,
            duration=duration,
            release_probability=release_prob,
            features={
                "compression_ratio": float(compression_ratio),
                "range_compress": float(rng_compress),
                "vol_accum": float(vol_accum),
                "duration_norm": float(clamp(duration / float(self.period), 0.0, 1.0)),
                "bbw_baseline": float(baseline),
                "bbw_latest": float(latest),
            },
        )
