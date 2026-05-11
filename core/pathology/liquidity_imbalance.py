"""M1C — Liquidity imbalance primitive (Appendix M1C + T).

OHLCV-only liquidity proxy. Three sub-components with uniform weights
(Appendix V): Amihud illiquidity, range efficiency, wick pressure.
Each sub-component is robustly z-scored and sigmoid-mapped to [0,1].
"""

from __future__ import annotations

import numpy as np

from core.pathology.metrics import EPS, clip01, robust_zscore, sigmoid
from core.schemas.market_state import MarketState

WINDOW: int = 48
SIGMOID_GAIN: float = 1.0

W_AMIHUD: float = 1.0 / 3.0
W_RANGE_EFF: float = 1.0 / 3.0
W_WICK: float = 1.0 / 3.0


class LiquidityImbalance:
    """OHLCV-derived liquidity fragility score."""

    def compute(self, state: MarketState) -> float:
        bars = state.window
        if len(bars) < 3:
            return 0.0
        closes = np.array([b.close for b in bars], dtype=np.float64)
        opens = np.array([b.open for b in bars], dtype=np.float64)
        highs = np.array([b.high for b in bars], dtype=np.float64)
        lows = np.array([b.low for b in bars], dtype=np.float64)
        volumes = np.array([b.volume for b in bars], dtype=np.float64)

        returns = np.abs(np.diff(closes))
        vols = volumes[1:]
        amihud_series = returns / np.maximum(vols, EPS)
        tr = highs - lows
        range_eff_series = tr / np.maximum(volumes, EPS)
        body = np.abs(closes - opens)
        upper = highs - np.maximum(opens, closes)
        lower = np.minimum(opens, closes) - lows
        wick_series = (upper + lower) / np.maximum(body, 1e-9)

        amihud_z = robust_zscore(float(amihud_series[-1]), amihud_series[:-1], window=WINDOW)
        range_z = robust_zscore(float(range_eff_series[-1]), range_eff_series[:-1], window=WINDOW)
        wick_z = robust_zscore(float(wick_series[-1]), wick_series[:-1], window=WINDOW)

        amihud_n = sigmoid(amihud_z, gain=SIGMOID_GAIN)
        range_n = sigmoid(range_z, gain=SIGMOID_GAIN)
        wick_n = sigmoid(wick_z, gain=SIGMOID_GAIN)

        combined = W_AMIHUD * amihud_n + W_RANGE_EFF * range_n + W_WICK * wick_n
        return clip01(combined)
