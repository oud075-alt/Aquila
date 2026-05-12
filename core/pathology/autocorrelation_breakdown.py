"""M1B — Autocorrelation breakdown primitive (Appendix M1B).

breakdown = 1 - |autocorr_t / baseline_autocorr|, clipped to [0,1].

Inputs: log returns over a 32-bar window. Baseline = lag-1 autocorrelation
over the broader available history (up to 256 bars). High breakdown means
continuation persistence is deteriorating.
"""

from __future__ import annotations

import numpy as np

from core.pathology.metrics import EPS, clip01, lag1_autocorr, log_returns
from core.schemas.market_state import MarketState

WINDOW: int = 32
BASELINE_WINDOW: int = 256


class AutocorrelationBreakdown:
    """Compute lag-1 autocorrelation breakdown against rolling baseline."""

    def compute(self, state: MarketState) -> float:
        closes = np.array(state.closes, dtype=np.float64)
        if len(closes) < WINDOW + 2:
            return 0.0
        rets = log_returns(closes)
        if len(rets) < WINDOW + 2:
            return 0.0
        recent = rets[-WINDOW:]
        baseline_slice = rets[-BASELINE_WINDOW:] if len(rets) >= BASELINE_WINDOW else rets
        ac_t = lag1_autocorr(recent)
        ac_base = lag1_autocorr(baseline_slice)
        if abs(ac_base) <= EPS:
            return clip01(1.0 - abs(ac_t))
        return clip01(1.0 - abs(ac_t / ac_base))
