"""M1D — Dispersion shock primitive (Appendix M1D).

dispersion = std(short_window_returns) / std(long_window_returns).
Normalization: rolling percentile rank.
"""

from __future__ import annotations

import numpy as np

from core.pathology.metrics import EPS, log_returns, percentile_rank
from core.schemas.market_state import MarketState

SHORT_WINDOW: int = 16
LONG_WINDOW: int = 64
HISTORY_WINDOW: int = 256


class DispersionShock:
    """Volatility regime fragmentation via short/long dispersion ratio."""

    def compute(self, state: MarketState) -> float:
        closes = np.array(state.closes, dtype=np.float64)
        if len(closes) < LONG_WINDOW + SHORT_WINDOW + 1:
            return 0.0
        rets = log_returns(closes)
        ratios = []
        upper = len(rets)
        start = max(LONG_WINDOW, SHORT_WINDOW)
        for i in range(start, upper + 1):
            short = rets[i - SHORT_WINDOW : i]
            long_ = rets[i - LONG_WINDOW : i]
            s = float(short.std()) + EPS
            l_ = float(long_.std()) + EPS
            ratios.append(s / l_)
        if not ratios:
            return 0.0
        history = np.array(ratios[-HISTORY_WINDOW:], dtype=np.float64)
        current = float(history[-1])
        return percentile_rank(current, history)
