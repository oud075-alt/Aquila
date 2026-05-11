"""Actual market behaviour engine.

Required by the mandatory intelligence flow: this engine measures what the
market *actually* did — independently from the expectation engine — so
contradictions can be computed directly.
"""

from __future__ import annotations

from typing import List

import numpy as np

from brain.math_core import (
    autocorrelation,
    bollinger_width,
    directional_coherence,
    safe_array,
    safe_div,
    shannon_entropy,
    slope_normalized,
    trend_efficiency,
)
from brain.schemas import ActualBehaviorProfile, Candle


class ActualBehaviorEngine:
    """Compute observed behaviour metrics from raw candles."""

    def __init__(self, lookback: int = 100, breakout_lookback: int = 60):
        self.lookback = lookback
        self.breakout_lookback = breakout_lookback

    def measure(self, candles: List[Candle]) -> ActualBehaviorProfile:
        if len(candles) < 30:
            return ActualBehaviorProfile()

        recent = candles[-self.lookback :] if len(candles) > self.lookback else candles
        closes = np.array([c.close for c in recent], dtype=np.float64)
        highs = np.array([c.high for c in recent], dtype=np.float64)
        lows = np.array([c.low for c in recent], dtype=np.float64)
        opens = np.array([c.open for c in recent], dtype=np.float64)
        volumes = np.array([c.volume for c in recent], dtype=np.float64)
        log_rets = np.diff(np.log(np.maximum(closes, 1e-12)))

        slope = slope_normalized(closes, min(50, closes.size - 2))
        efficiency = trend_efficiency(closes, min(30, closes.size - 1))
        persistence = max(0.0, autocorrelation(log_rets, lag=1))
        rv = float(np.std(log_rets, ddof=1)) if log_rets.size > 1 else 0.0
        atr_proxy = float(np.mean(highs - lows)) if highs.size else 0.0

        median_vol = float(np.median(volumes)) or 1e-9
        participation = float(np.mean(volumes[-20:]) / median_vol)

        # Acceptance: fraction of last 30 bars closing in the "value area"
        # (mean +/- 1 std of recent closes).
        recent_closes = closes[-60:]
        mean_c = float(np.mean(recent_closes))
        std_c = float(np.std(recent_closes, ddof=1)) or 1e-9
        in_value = np.abs(closes[-30:] - mean_c) <= std_c
        acceptance = float(np.mean(in_value)) if in_value.size else 0.0

        # Breakout follow-through: measure the actual cumulative return
        # over the next 5 bars after the largest absolute move in lookback.
        if log_rets.size > self.breakout_lookback + 5:
            window = log_rets[-self.breakout_lookback :]
            idx_local = int(np.argmax(np.abs(window)))
            idx_global = log_rets.size - self.breakout_lookback + idx_local
            direction = float(np.sign(log_rets[idx_global]))
            future = log_rets[idx_global + 1 : idx_global + 6]
            followthrough = float(direction * np.sum(future) / (abs(log_rets[idx_global]) + 1e-12))
            followthrough = max(-1.5, min(2.0, followthrough))
        else:
            followthrough = 0.0

        # Pullback depth: max drawdown from rolling peak in last 50 bars.
        peak = closes[-50:].max() if closes.size >= 50 else closes.max()
        trough = closes[-50:].min() if closes.size >= 50 else closes.min()
        pullback_depth = float(safe_div(peak - trough, peak, default=0.0))

        # Compression release: ratio of latest bb width vs. its rolling median
        bbw = bollinger_width(closes, 20, 2.0)
        compression_release = float(safe_div(bbw[-1], float(np.median(bbw[-50:])), 1.0)) if bbw.size > 10 else 1.0

        # Wick / body ratios
        bodies = np.abs(closes - opens)
        ranges = (highs - lows)
        wick = ranges - bodies
        wick_body_ratio = float(safe_div(float(np.mean(wick)), float(np.mean(bodies)) or 1e-9, 0.0))

        # Rejection intensity: how many of the last 20 bars had a large wick
        # relative to body and closed in the opposite direction of the wick.
        rejection_score = 0.0
        recent_count = min(20, recent.__len__())
        for i in range(-recent_count, 0):
            c = recent[i]
            rng = c.range or 1e-9
            up_wick_ratio = c.upper_wick / rng
            dn_wick_ratio = c.lower_wick / rng
            if up_wick_ratio > 0.55 and c.close < c.open:
                rejection_score += 1.0
            elif dn_wick_ratio > 0.55 and c.close > c.open:
                rejection_score += 1.0
        rejection_intensity = float(rejection_score / max(1, recent_count))

        # Momentum persistence: lag-1..lag-5 autocorrelation mean
        ac = [max(0.0, autocorrelation(log_rets, lag=k)) for k in range(1, 6)]
        momentum_persistence = float(np.mean(ac))

        return ActualBehaviorProfile(
            realized_trend_slope=float(slope),
            realized_continuation_persistence=float(persistence),
            realized_volatility=float(rv),
            realized_atr=float(atr_proxy),
            realized_participation=float(participation),
            realized_acceptance=float(acceptance),
            realized_efficiency=float(efficiency),
            realized_breakout_followthrough=float(followthrough),
            realized_pullback_depth=float(pullback_depth),
            realized_compression_release_ratio=float(compression_release),
            wick_body_ratio=float(wick_body_ratio),
            rejection_intensity=float(rejection_intensity),
            momentum_persistence=float(momentum_persistence),
            metadata={
                "directional_coherence": float(directional_coherence(log_rets)),
                "entropy": float(shannon_entropy(log_rets)),
                "median_volume": float(median_vol),
            },
        )
