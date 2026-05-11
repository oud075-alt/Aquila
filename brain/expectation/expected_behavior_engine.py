"""Expected-behaviour engine — orchestrates the per-regime expectation models.

Given a raw market snapshot the engine produces a single
:class:`ExpectationProfile` describing what a healthy market in the same
regime should look like.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from brain.expectation.continuation_expectation import ContinuationExpectationModel
from brain.expectation.healthy_trend_model import HealthyTrendModel
from brain.expectation.market_regime_model import MarketRegimeModel
from brain.expectation.volatility_expectation import VolatilityExpectationModel
from brain.math_core import linear_regression
from brain.schemas import Candle, ExpectationProfile, RegimeLabel


class ExpectedBehaviorEngine:
    def __init__(self):
        self.regime_model = MarketRegimeModel()
        self.trend_model = HealthyTrendModel()
        self.continuation_model = ContinuationExpectationModel()
        self.volatility_model = VolatilityExpectationModel()

    def build(self, candles: List[Candle]) -> ExpectationProfile:
        regime = self.regime_model.evaluate(candles)
        trend_exp = self.trend_model.expect(candles)
        cont_exp = self.continuation_model.expect(candles, regime.label)
        vol_exp = self.volatility_model.expect(candles)

        # Healthy participation expectation: median volume of last N
        volumes = np.array([c.volume for c in candles[-200:]], dtype=np.float64) if candles else np.array([0.0])
        median_vol = float(np.median(volumes)) if volumes.size else 0.0

        # Healthy acceptance: fraction of bars closing inside healthy band.
        if len(candles) >= 60:
            closes = np.array([c.close for c in candles[-60:]])
            x = np.arange(closes.size)
            slope, intercept, _ = linear_regression(x, closes)
            fitted = slope * x + intercept
            band = float(np.std(closes - fitted)) or 1e-9
            inside = np.abs(closes - fitted) <= (1.5 * band)
            healthy_acceptance = float(np.mean(inside))
        else:
            healthy_acceptance = 0.75

        # Regime-conditioned expected_efficiency override
        efficiency_floor = {
            RegimeLabel.TREND_UP: 0.55,
            RegimeLabel.TREND_DOWN: 0.55,
            RegimeLabel.EXPANSION: 0.45,
            RegimeLabel.COMPRESSION: 0.25,
            RegimeLabel.MEAN_REVERSION: 0.20,
            RegimeLabel.CHAOTIC: 0.15,
        }.get(regime.label, 0.30)

        profile = ExpectationProfile(
            regime=regime.label,
            expected_trend_slope=float(trend_exp.expected_slope),
            expected_continuation_persistence=float(
                max(cont_exp.expected_persistence, trend_exp.expected_persistence)
            ),
            expected_volatility=float(vol_exp.expected_vol),
            expected_atr=float(vol_exp.expected_atr),
            expected_participation=float(median_vol),
            expected_acceptance=float(healthy_acceptance),
            expected_efficiency=float(max(efficiency_floor, trend_exp.expected_efficiency)),
            expected_breakout_followthrough=float(cont_exp.expected_followthrough),
            expected_pullback_depth=float(trend_exp.expected_pullback_depth),
            expected_compression_release_ratio=float(cont_exp.expected_compression_release),
            regime_confidence=float(regime.confidence),
            metadata={
                "regime_features": regime.features,
                "trend_features": trend_exp.features,
                "continuation_features": cont_exp.features,
                "volatility_features": vol_exp.features,
            },
        )
        return profile
