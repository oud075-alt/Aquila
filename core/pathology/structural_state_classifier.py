"""Structural state classifier (Appendix U + ADR-0001).

SOLE authority for assigning a `StructuralState` label per bar. Other modules
MUST consume this output rather than re-deriving labels.
"""

from __future__ import annotations

import numpy as np

from core.pathology.metrics import (
    directional_efficiency,
    momentum_sign_flipped,
    robust_zscore,
    rolling_range,
    trend_slope,
    wick_pressure_from_ohlc,
    wilder_atr,
)
from core.schemas.enums import StructuralState
from core.schemas.market_state import MarketBar, MarketState

ATR_PERIOD: int = 64
EFFICIENCY_WINDOW: int = 32
SLOPE_WINDOW: int = 32
ROBUST_WINDOW: int = 64

COMPRESSION_RATIO: float = 0.50
EXPANSION_RATIO: float = 1.50
DIRECTIONAL_EFFICIENCY_THRESHOLD: float = 0.60
VOLUME_ZSCORE_LOW: float = -1.00
RANGE_ZSCORE_LOW: float = -0.50
WICK_PRESSURE_REVERSAL_MULTIPLIER: float = 2.0


class StructuralStateClassifier:
    """Deterministic single-value classifier (Appendix U + ADR-0001 priority)."""

    def classify(self, state: MarketState) -> StructuralState:
        current = state.current_bar
        bars = state.window
        if len(bars) < 4:
            return StructuralState.CHAOTIC_TRANSITION

        highs = np.array([b.high for b in bars], dtype=np.float64)
        lows = np.array([b.low for b in bars], dtype=np.float64)
        closes = np.array([b.close for b in bars], dtype=np.float64)
        volumes = np.array([b.volume for b in bars], dtype=np.float64)
        ranges = highs - lows

        atr64 = wilder_atr(highs, lows, closes, period=ATR_PERIOD)
        rng = rolling_range(highs, lows)
        ratio = rng / max(atr64, 1e-9)

        de = directional_efficiency(closes, window=EFFICIENCY_WINDOW)
        slope = trend_slope(closes, window=SLOPE_WINDOW)

        vol_z = robust_zscore(float(volumes[-1]), volumes[:-1], window=ROBUST_WINDOW)
        rng_z = robust_zscore(float(ranges[-1]), ranges[:-1], window=ROBUST_WINDOW)

        wp = wick_pressure_from_ohlc(current.open, current.high, current.low, current.close)
        flipped = momentum_sign_flipped(closes)

        body = abs(current.close - current.open)

        if (current.high - max(current.open, current.close)) + (
            min(current.open, current.close) - current.low
        ) > body * WICK_PRESSURE_REVERSAL_MULTIPLIER and flipped:
            return StructuralState.REVERSAL_PRESSURE

        if vol_z < VOLUME_ZSCORE_LOW and rng_z < RANGE_ZSCORE_LOW:
            return StructuralState.LIQUIDITY_STALL

        if ratio > EXPANSION_RATIO:
            return StructuralState.VOLATILITY_EXPANSION

        if ratio < COMPRESSION_RATIO:
            return StructuralState.COMPRESSION

        if (
            current.close > current.open
            and de > DIRECTIONAL_EFFICIENCY_THRESHOLD
            and slope > 0
        ):
            return StructuralState.UP_CONTINUATION

        if (
            current.close < current.open
            and de > DIRECTIONAL_EFFICIENCY_THRESHOLD
            and slope < 0
        ):
            return StructuralState.DOWN_CONTINUATION

        _ = wp
        return StructuralState.CHAOTIC_TRANSITION

    def classify_window(self, bars: tuple[MarketBar, ...]) -> list[StructuralState]:
        """Classify each bar treating the prefix up to that bar as its window."""
        labels: list[StructuralState] = []
        for i in range(len(bars)):
            window = bars[: i + 1]
            tail = window[:-1]
            current = window[-1]
            synthetic = MarketState(
                timestamp=current.timestamp,
                timeframe=current.timeframe,
                source=current.source,
                confidence=1.0,
                symbol=current.symbol,
                current_bar=current,
                tail=tail,
            )
            labels.append(self.classify(synthetic))
        return labels
