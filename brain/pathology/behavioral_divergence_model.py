"""Behavioural divergence model.

Quantifies contradictions between *internal* metrics that should normally
move together:

* price vs RSI
* price vs cumulative delta (proxy: signed body * volume)
* price vs volume trend
* range vs body share
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import clamp, linear_regression, rsi, safe_div
from brain.schemas import Candle


@dataclass
class DivergenceAssessment:
    score: float
    features: Dict[str, float]


class BehavioralDivergenceModel:
    def __init__(self, window: int = 60):
        self.window = window

    def evaluate(self, candles: List[Candle]) -> DivergenceAssessment:
        if len(candles) < self.window + 5:
            return DivergenceAssessment(0.0, {})

        recent = candles[-self.window :]
        closes = np.array([c.close for c in recent], dtype=np.float64)
        volumes = np.array([c.volume for c in recent], dtype=np.float64)
        bodies = np.array([c.body for c in recent], dtype=np.float64)
        ranges = np.array([c.range for c in recent], dtype=np.float64)
        signs = np.array([1.0 if c.is_bullish else -1.0 for c in recent], dtype=np.float64)

        x = np.arange(self.window, dtype=np.float64)
        price_slope, _, _ = linear_regression(x, closes)

        rsi_series = rsi(closes, period=14)
        rsi_slope, _, _ = linear_regression(x[-rsi_series.size :], rsi_series)

        delta_cum = np.cumsum(signs * bodies * volumes)
        delta_slope, _, _ = linear_regression(x, delta_cum)

        vol_slope, _, _ = linear_regression(x, volumes)
        body_share = bodies / (ranges + 1e-9)
        body_share_slope, _, _ = linear_regression(x, body_share)

        # Divergence flags (sign mismatch with magnitude)
        def _divergence(a: float, b: float) -> float:
            if abs(a) < 1e-12 or abs(b) < 1e-12:
                return 0.0
            if np.sign(a) == np.sign(b):
                return 0.0
            scale = max(abs(a), abs(b))
            return clamp(scale * 200.0, 0.0, 1.0)

        price_rsi = _divergence(price_slope, rsi_slope)
        price_delta = _divergence(price_slope, delta_slope)
        price_vol = _divergence(price_slope, vol_slope)
        body_share_decline = clamp(-body_share_slope * 100.0, 0.0, 1.0)

        score = clamp(
            0.30 * price_rsi
            + 0.30 * price_delta
            + 0.20 * price_vol
            + 0.20 * body_share_decline,
            0.0,
            1.0,
        )

        return DivergenceAssessment(
            score=score,
            features={
                "price_vs_rsi": float(price_rsi),
                "price_vs_delta": float(price_delta),
                "price_vs_volume": float(price_vol),
                "body_share_decline": float(body_share_decline),
                "price_slope": float(price_slope),
            },
        )
