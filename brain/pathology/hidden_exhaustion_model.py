"""Hidden exhaustion model.

Detects momentum/participation deterioration *while price still extends*.
Symptoms:
* RSI / momentum diverges from price highs
* Volume declines while range extends
* Body shrinkage in last N bars
* Trend efficiency drops despite new highs/lows
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import clamp, linear_regression, momentum, rsi, safe_div
from brain.schemas import Candle


@dataclass
class ExhaustionAssessment:
    score: float
    features: Dict[str, float]


class HiddenExhaustionModel:
    def __init__(self, window: int = 40):
        self.window = window

    def evaluate(self, candles: List[Candle]) -> ExhaustionAssessment:
        if len(candles) < self.window + 5:
            return ExhaustionAssessment(0.0, {})

        recent = candles[-self.window :]
        closes = np.array([c.close for c in recent], dtype=np.float64)
        volumes = np.array([c.volume for c in recent], dtype=np.float64)
        bodies = np.array([c.body for c in recent], dtype=np.float64)

        # Detect trend direction (price slope)
        x = np.arange(self.window, dtype=np.float64)
        price_slope, _, _ = linear_regression(x, closes)

        # Momentum slope (should track price slope when healthy)
        mom = momentum(closes, period=10)
        mom_slope, _, _ = linear_regression(x, mom)

        # Divergence between price and momentum slope
        divergence_strength = 0.0
        if abs(price_slope) > 1e-9 and abs(mom_slope) > 1e-9:
            denom = abs(price_slope) + abs(mom_slope)
            divergence_strength = max(0.0, -np.sign(price_slope) * np.sign(mom_slope))
            divergence_strength *= safe_div(abs(price_slope - mom_slope), denom, 0.0)
        # If signs differ outright, divergence is at least 0.5
        if np.sign(price_slope) * np.sign(mom_slope) < 0:
            divergence_strength = max(divergence_strength, 0.6)

        # RSI divergence with price: compare slopes
        rsi_series = rsi(closes, period=14)
        rsi_slope, _, _ = linear_regression(x[-rsi_series.size :], rsi_series)
        rsi_divergence = 0.0
        if abs(price_slope) > 1e-9 and abs(rsi_slope) > 1e-9:
            if np.sign(price_slope) != np.sign(rsi_slope):
                rsi_divergence = clamp(abs(price_slope) + abs(rsi_slope), 0.0, 1.0)

        # Volume decay while price extends
        vol_slope, _, _ = linear_regression(x, volumes)
        vol_decay = 0.0
        if price_slope > 0 and vol_slope < 0:
            vol_decay = clamp(abs(vol_slope) / (np.mean(volumes) + 1e-9) * 50.0, 0.0, 1.0)
        elif price_slope < 0 and vol_slope < 0:
            vol_decay = clamp(abs(vol_slope) / (np.mean(volumes) + 1e-9) * 30.0, 0.0, 1.0)

        # Body shrinkage: last N body mean / earlier body mean
        half = self.window // 2
        body_recent = float(np.mean(bodies[-half:])) or 1e-9
        body_earlier = float(np.mean(bodies[:half])) or 1e-9
        body_shrink = clamp((body_earlier - body_recent) / body_earlier, 0.0, 1.0)

        score = clamp(
            0.40 * divergence_strength
            + 0.25 * rsi_divergence
            + 0.20 * vol_decay
            + 0.15 * body_shrink,
            0.0,
            1.0,
        )

        return ExhaustionAssessment(
            score=score,
            features={
                "price_slope": float(price_slope),
                "momentum_slope": float(mom_slope),
                "rsi_slope": float(rsi_slope),
                "volume_slope": float(vol_slope),
                "divergence_strength": float(divergence_strength),
                "rsi_divergence": float(rsi_divergence),
                "volume_decay": float(vol_decay),
                "body_shrink": float(body_shrink),
            },
        )
