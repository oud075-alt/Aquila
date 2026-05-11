"""Healthy trend model.

Defines what "healthy" continuation, momentum persistence and pullback
recovery look like in a directional regime. The model returns expectations
the orchestrator can compare against actual market behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import (
    autocorrelation,
    linear_regression,
    safe_array,
    trend_efficiency,
)
from brain.schemas import Candle


@dataclass
class HealthyTrendExpectation:
    expected_slope: float
    expected_efficiency: float
    expected_persistence: float
    expected_pullback_depth: float
    r_squared: float
    features: Dict[str, float]


class HealthyTrendModel:
    """Calibrated baseline for healthy directional behaviour."""

    def __init__(
        self,
        trend_window: int = 50,
        persistence_lag: int = 3,
        min_r2: float = 0.55,
    ):
        self.trend_window = trend_window
        self.persistence_lag = persistence_lag
        self.min_r2 = min_r2

    def expect(self, candles: List[Candle]) -> HealthyTrendExpectation:
        if len(candles) < self.trend_window + 5:
            return HealthyTrendExpectation(0, 0, 0, 0, 0, {})

        closes = np.array([c.close for c in candles], dtype=np.float64)
        log_closes = np.log(np.maximum(closes, 1e-12))
        x = np.arange(self.trend_window, dtype=np.float64)
        y = log_closes[-self.trend_window :]
        slope, intercept, r2 = linear_regression(x, y)
        efficiency = trend_efficiency(closes, self.trend_window)

        rets = np.diff(log_closes[-self.trend_window * 2 :])
        persistence = max(0.0, autocorrelation(rets, lag=self.persistence_lag))

        # Healthy pullback depth ~ 0.382 of recent swing (Fibonacci-derived heuristic
        # validated by simply measuring drawdown of recent linear regression model).
        residuals = y - (slope * x + intercept)
        atr_proxy = float(np.std(residuals))
        median_price = float(np.median(closes[-self.trend_window:]))
        expected_pullback = float(0.382 * atr_proxy / max(median_price, 1e-9))

        features = {
            "log_slope": float(slope),
            "r_squared": float(r2),
            "efficiency": float(efficiency),
            "persistence_lag_acorr": float(persistence),
            "atr_proxy_residual": float(atr_proxy),
        }

        return HealthyTrendExpectation(
            expected_slope=float(slope),
            expected_efficiency=float(max(0.45, efficiency)),
            expected_persistence=float(max(0.45, persistence)),
            expected_pullback_depth=float(expected_pullback),
            r_squared=float(r2),
            features=features,
        )
