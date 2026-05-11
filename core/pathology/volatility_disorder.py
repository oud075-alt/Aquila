"""M1E — Volatility disorder primitive (Appendix M1E).

volatility_disorder = std(realized_vol_window) / mean(realized_vol_window).
Window = 48 bars of realized vol (rolling 16-bar std of log returns).
Normalized via robust z-score + sigmoid.
"""

from __future__ import annotations

import numpy as np

from core.pathology.metrics import EPS, clip01, log_returns, robust_zscore, sigmoid
from core.schemas.market_state import MarketState

REALIZED_WINDOW: int = 16
DISORDER_WINDOW: int = 48
HISTORY_WINDOW: int = 256
SIGMOID_GAIN: float = 1.0


class VolatilityDisorder:
    """Coefficient-of-variation of realized volatility."""

    def compute(self, state: MarketState) -> float:
        closes = np.array(state.closes, dtype=np.float64)
        if len(closes) < REALIZED_WINDOW + DISORDER_WINDOW + 1:
            return 0.0
        rets = log_returns(closes)
        rv_series = []
        for i in range(REALIZED_WINDOW, len(rets) + 1):
            rv_series.append(float(rets[i - REALIZED_WINDOW : i].std()))
        rv = np.array(rv_series, dtype=np.float64)
        if len(rv) < DISORDER_WINDOW:
            return 0.0
        window = rv[-DISORDER_WINDOW:]
        mean = float(window.mean())
        std = float(window.std())
        if mean <= EPS:
            return 0.0
        cov = std / mean
        history = []
        for i in range(DISORDER_WINDOW, len(rv) + 1):
            w = rv[i - DISORDER_WINDOW : i]
            m = float(w.mean())
            if m > EPS:
                history.append(float(w.std()) / m)
        history_arr = np.array(history[-HISTORY_WINDOW:], dtype=np.float64) if history else np.array([cov])
        z = robust_zscore(cov, history_arr, window=HISTORY_WINDOW)
        return clip01(sigmoid(z, gain=SIGMOID_GAIN))
