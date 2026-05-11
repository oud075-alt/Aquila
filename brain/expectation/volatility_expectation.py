"""Volatility expectation model.

Combines an EWMA + GARCH-like volatility forecast to estimate what a
healthy realised volatility *should* look like. Used by the contradiction
engine to detect stress build-ups (vol below expectation while pressure
accumulates) or unstable expansion (vol far above expectation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import ewma, realized_volatility, safe_array
from brain.schemas import Candle


@dataclass
class VolatilityExpectation:
    expected_vol: float
    expected_atr: float
    upper_band: float
    lower_band: float
    persistence_alpha: float
    features: Dict[str, float]


class VolatilityExpectationModel:
    """Hybrid EWMA + simple GARCH(1,1) baseline."""

    def __init__(self, ewma_span: int = 20, garch_omega: float = 1e-6,
                 garch_alpha: float = 0.10, garch_beta: float = 0.86):
        self.ewma_span = ewma_span
        self.omega = garch_omega
        self.alpha = garch_alpha
        self.beta = garch_beta

    def expect(self, candles: List[Candle]) -> VolatilityExpectation:
        if len(candles) < 40:
            return VolatilityExpectation(0, 0, 0, 0, 0, {})

        closes = np.array([c.close for c in candles], dtype=np.float64)
        log_rets = np.diff(np.log(np.maximum(closes, 1e-12)))
        if log_rets.size < 30:
            return VolatilityExpectation(0, 0, 0, 0, 0, {})

        # EWMA volatility
        sq = log_rets ** 2
        ew = ewma(sq, span=self.ewma_span)
        ewma_vol = float(np.sqrt(ew[-1]))

        # Simple GARCH(1,1) recursion
        var_series = np.zeros_like(sq)
        var_series[0] = float(np.var(log_rets[:20])) if log_rets.size >= 20 else 1e-8
        for i in range(1, sq.size):
            var_series[i] = self.omega + self.alpha * sq[i - 1] + self.beta * var_series[i - 1]
        garch_vol = float(np.sqrt(var_series[-1]))

        expected_vol = float(0.6 * ewma_vol + 0.4 * garch_vol)
        # ATR equivalent: vol * price (approximation of average move)
        last_close = float(closes[-1])
        expected_atr = expected_vol * last_close

        realized = realized_volatility(log_rets[-self.ewma_span:])
        deviation = float(realized - expected_vol)
        upper = expected_vol * 1.6
        lower = expected_vol * 0.6
        persistence = float(self.alpha + self.beta)

        features = {
            "ewma_vol": ewma_vol,
            "garch_vol": garch_vol,
            "realized": realized,
            "deviation": deviation,
        }

        return VolatilityExpectation(
            expected_vol=expected_vol,
            expected_atr=expected_atr,
            upper_band=upper,
            lower_band=lower,
            persistence_alpha=persistence,
            features=features,
        )
