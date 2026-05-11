"""Continuation expectation model.

Estimates how strongly a healthy market *should* continue once a breakout
or expansion event has been detected. The model is purely empirical: it
measures past breakouts on the same series to derive realistic follow-
through and persistence baselines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import autocorrelation, atr, safe_array
from brain.schemas import Candle, RegimeLabel


@dataclass
class ContinuationExpectation:
    expected_followthrough: float
    expected_persistence: float
    expected_runlength: float
    expected_compression_release: float
    features: Dict[str, float]


class ContinuationExpectationModel:
    def __init__(self, lookback: int = 200, breakout_z: float = 1.5):
        self.lookback = lookback
        self.breakout_z = breakout_z

    def expect(self, candles: List[Candle], regime: RegimeLabel) -> ContinuationExpectation:
        if len(candles) < 60:
            return ContinuationExpectation(0.5, 0.5, 5.0, 1.0, {})

        recent = candles[-self.lookback :] if len(candles) > self.lookback else candles
        closes = np.array([c.close for c in recent], dtype=np.float64)
        highs = np.array([c.high for c in recent], dtype=np.float64)
        lows = np.array([c.low for c in recent], dtype=np.float64)
        log_rets = np.diff(np.log(np.maximum(closes, 1e-12)))
        atr_series = atr(highs, lows, closes, period=14)
        atr_value = float(atr_series[-1]) if atr_series.size else 0.0

        # Detect historical breakouts: log-returns >z above rolling mean.
        if log_rets.size < 30:
            return ContinuationExpectation(0.5, 0.5, 5.0, 1.0, {})
        mu = float(np.mean(log_rets))
        sigma = float(np.std(log_rets, ddof=1)) or 1e-9
        z = (log_rets - mu) / sigma
        breakout_idx = np.where(np.abs(z) > self.breakout_z)[0]

        followthrough_samples: List[float] = []
        runlength_samples: List[int] = []
        for i in breakout_idx:
            direction = np.sign(log_rets[i])
            run = 0
            cumulative = 0.0
            for j in range(i + 1, min(i + 10, log_rets.size)):
                if np.sign(log_rets[j]) == direction:
                    run += 1
                    cumulative += abs(log_rets[j])
                else:
                    break
            if run > 0:
                followthrough_samples.append(cumulative / abs(log_rets[i] + 1e-12))
                runlength_samples.append(run)

        expected_followthrough = float(np.median(followthrough_samples)) if followthrough_samples else 0.4
        expected_runlength = float(np.median(runlength_samples)) if runlength_samples else 3.0
        expected_persistence = max(0.0, autocorrelation(log_rets, lag=1))

        # Compression-release expectation: ratio of ATR spike right after
        # a compression cluster (lowest 10% bb width).
        from brain.math_core import bollinger_width

        bbw = bollinger_width(closes, period=20, k=2.0)
        if bbw.size > 30:
            thresh = float(np.quantile(bbw, 0.1))
            compression_idx = np.where(bbw[:-5] <= thresh)[0]
            release_ratios = []
            for i in compression_idx:
                pre_slice = atr_series[max(0, i - 10) : i]
                post_slice = atr_series[i : i + 10]
                if pre_slice.size == 0 or post_slice.size == 0:
                    continue
                pre = float(np.mean(pre_slice))
                post = float(np.mean(post_slice))
                if pre > 0:
                    release_ratios.append(post / pre)
            expected_compression_release = float(np.median(release_ratios)) if release_ratios else 1.25
        else:
            expected_compression_release = 1.25

        regime_modifier = {
            RegimeLabel.TREND_UP: 1.10,
            RegimeLabel.TREND_DOWN: 1.10,
            RegimeLabel.EXPANSION: 1.15,
            RegimeLabel.COMPRESSION: 0.85,
            RegimeLabel.MEAN_REVERSION: 0.70,
            RegimeLabel.CHAOTIC: 0.50,
        }.get(regime, 1.0)
        expected_followthrough *= regime_modifier
        expected_persistence *= regime_modifier

        features = {
            "n_breakouts": float(breakout_idx.size),
            "atr_value": atr_value,
            "regime_modifier": regime_modifier,
        }

        return ContinuationExpectation(
            expected_followthrough=float(min(2.0, max(0.0, expected_followthrough))),
            expected_persistence=float(min(1.0, max(0.0, expected_persistence))),
            expected_runlength=float(max(1.0, expected_runlength)),
            expected_compression_release=float(min(3.0, max(0.5, expected_compression_release))),
            features=features,
        )
