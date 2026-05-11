"""Stress escalation model.

Tracks the build-up of structural stress: rising vol-of-vol, increasing
wick ratios, rising rejection events and accelerating sweep activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import clamp, ewma, linear_regression
from brain.schemas import Candle
from brain.sensory.volatility_tracker import VolatilityTracker, VolatilityReading


@dataclass
class StressAssessment:
    score: float
    velocity: float
    features: Dict[str, float]


class StressEscalationModel:
    def __init__(self, window: int = 50):
        self.window = window
        self.tracker = VolatilityTracker(short_window=20, long_window=100)

    def evaluate(self, candles: List[Candle]) -> StressAssessment:
        if len(candles) < self.window + 5:
            return StressAssessment(0.0, 0.0, {})

        recent = candles[-self.window :]
        ranges = np.array([c.range for c in recent], dtype=np.float64)
        bodies = np.array([c.body for c in recent], dtype=np.float64)
        upper = np.array([c.upper_wick for c in recent], dtype=np.float64)
        lower = np.array([c.lower_wick for c in recent], dtype=np.float64)
        wick = upper + lower

        wick_body_ratio = wick / (bodies + 1e-9)
        wick_ratio_smoothed = ewma(wick_body_ratio, span=10)
        x = np.arange(wick_ratio_smoothed.size, dtype=np.float64)
        wick_slope, _, _ = linear_regression(x, wick_ratio_smoothed)
        wick_pressure = clamp(wick_slope * 20.0 + np.mean(wick_ratio_smoothed[-5:]) / 3.0, 0.0, 1.0)

        # Vol-of-vol trend
        vol_reading: VolatilityReading = self.tracker.measure(candles)
        vov_trend = clamp(vol_reading.vol_of_vol * 200.0, 0.0, 1.0)

        # Rejection density (large opposite wicks closing against)
        rejection_count = 0
        for c in recent:
            if c.range < 1e-9:
                continue
            up = c.upper_wick / c.range
            dn = c.lower_wick / c.range
            if (up > 0.55 and c.close < c.open) or (dn > 0.55 and c.close > c.open):
                rejection_count += 1
        rejection_density = clamp(rejection_count / self.window * 2.0, 0.0, 1.0)

        # Range expansion velocity
        rng_ewma = ewma(ranges, span=10)
        rng_slope, _, _ = linear_regression(x, rng_ewma)
        baseline = float(np.mean(rng_ewma)) or 1e-9
        rng_velocity = clamp(rng_slope / baseline * 30.0, 0.0, 1.0)

        score = clamp(
            0.30 * wick_pressure
            + 0.25 * vov_trend
            + 0.25 * rejection_density
            + 0.20 * rng_velocity,
            0.0,
            1.0,
        )

        velocity = clamp((wick_slope * 50.0) + (rng_slope / baseline * 50.0), -1.0, 1.0)

        return StressAssessment(
            score=score,
            velocity=float(velocity),
            features={
                "wick_pressure": float(wick_pressure),
                "vol_of_vol": float(vov_trend),
                "rejection_density": float(rejection_density),
                "range_velocity": float(rng_velocity),
            },
        )
