"""Market regime classification.

Identifies the dominant regime (trend up/down, compression, expansion,
mean-reversion, chaotic) from price/volatility/entropy features. The
expectation engine uses the regime to choose the correct physiology model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import (
    bollinger_width,
    directional_coherence,
    realized_volatility,
    shannon_entropy,
    slope_normalized,
    trend_efficiency,
)
from brain.schemas import Candle, RegimeLabel


@dataclass
class RegimeAssessment:
    label: RegimeLabel
    confidence: float
    features: Dict[str, float]


class MarketRegimeModel:
    def __init__(self, slope_period: int = 50, efficiency_period: int = 30):
        self.slope_period = slope_period
        self.efficiency_period = efficiency_period

    def evaluate(self, candles: List[Candle]) -> RegimeAssessment:
        if len(candles) < self.slope_period + 5:
            return RegimeAssessment(RegimeLabel.COMPRESSION, 0.1, {})

        closes = np.array([c.close for c in candles], dtype=np.float64)
        rets = np.diff(np.log(np.maximum(closes, 1e-12)))

        slope = slope_normalized(closes, self.slope_period)
        efficiency = trend_efficiency(closes, self.efficiency_period)
        coherence = directional_coherence(rets[-self.slope_period:])
        ent = shannon_entropy(rets[-self.slope_period:])
        bbw = float(bollinger_width(closes, 20, 2.0)[-1])
        baseline_bbw = float(np.mean(bollinger_width(closes, 20, 2.0)[-100:]))
        compression_ratio = float(max(0.0, 1.0 - bbw / (baseline_bbw + 1e-12)))
        rv = realized_volatility(rets[-50:])
        rv_long = realized_volatility(rets[-200:]) if rets.size > 200 else rv
        expansion_ratio = float(rv / (rv_long + 1e-12))

        features = {
            "slope": slope,
            "efficiency": efficiency,
            "coherence": coherence,
            "entropy": ent,
            "compression": compression_ratio,
            "expansion": expansion_ratio,
        }

        # Decision logic — explicit, ranked, deterministic.
        if ent > 0.85 and coherence < 0.45:
            return RegimeAssessment(RegimeLabel.CHAOTIC, min(1.0, ent), features)
        if compression_ratio > 0.55 and expansion_ratio < 1.0:
            return RegimeAssessment(RegimeLabel.COMPRESSION, min(1.0, compression_ratio), features)
        if expansion_ratio > 1.25 and efficiency > 0.35:
            return RegimeAssessment(RegimeLabel.EXPANSION, min(1.0, (expansion_ratio - 1.0)), features)
        if efficiency > 0.40 and abs(slope) > 0.0008:
            label = RegimeLabel.TREND_UP if slope > 0 else RegimeLabel.TREND_DOWN
            return RegimeAssessment(label, min(1.0, efficiency + abs(slope) * 200), features)
        return RegimeAssessment(RegimeLabel.MEAN_REVERSION, max(0.2, 1.0 - efficiency), features)
