"""Volatility tracker — realised vol, vol-of-vol, compression/expansion ratios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import atr, bollinger_width, realized_volatility, safe_array
from brain.schemas import Candle


@dataclass
class VolatilityReading:
    realized_vol: float
    short_vol: float
    long_vol: float
    vol_of_vol: float
    atr_value: float
    atr_expansion: float        # > 1 ⇒ expanding
    bb_width: float
    bb_compression: float       # 0 (no compression) → 1 (extreme compression)
    regime: str                 # "compression" | "expansion" | "normal"

    def to_dict(self) -> Dict[str, object]:
        return self.__dict__


class VolatilityTracker:
    def __init__(self, short_window: int = 20, long_window: int = 100, bb_period: int = 20, bb_k: float = 2.0):
        self.short_window = short_window
        self.long_window = long_window
        self.bb_period = bb_period
        self.bb_k = bb_k

    def measure(self, candles: List[Candle]) -> VolatilityReading:
        if len(candles) < self.short_window + 2:
            return VolatilityReading(0, 0, 0, 0, 0, 1.0, 0, 0, "normal")

        closes = np.array([c.close for c in candles], dtype=np.float64)
        highs = np.array([c.high for c in candles], dtype=np.float64)
        lows = np.array([c.low for c in candles], dtype=np.float64)
        rets = np.diff(np.log(np.maximum(closes, 1e-12)))

        short_vol = realized_volatility(rets[-self.short_window :])
        long_vol = realized_volatility(rets[-self.long_window :])
        realized = realized_volatility(rets[-self.short_window * 2 :])

        # Vol-of-vol from rolling std of returns
        roll = []
        for i in range(self.short_window, rets.size):
            roll.append(float(np.std(rets[i - self.short_window : i], ddof=1)))
        roll_arr = safe_array(roll)
        vol_of_vol = float(np.std(roll_arr, ddof=1)) if roll_arr.size > 2 else 0.0

        atr_series = atr(highs, lows, closes, period=14)
        atr_value = float(atr_series[-1])
        atr_baseline = float(np.mean(atr_series[-self.long_window :])) if atr_series.size else atr_value
        atr_expansion = float(atr_value / (atr_baseline + 1e-12))

        bbw = bollinger_width(closes, period=self.bb_period, k=self.bb_k)
        bb_width = float(bbw[-1])
        baseline_bbw = float(np.mean(bbw[-self.long_window :])) if bbw.size else bb_width
        compression = float(max(0.0, 1.0 - bb_width / (baseline_bbw + 1e-12)))
        compression = float(min(1.0, compression))

        if compression > 0.65 and atr_expansion < 0.9:
            regime = "compression"
        elif atr_expansion > 1.25 and bb_width > baseline_bbw:
            regime = "expansion"
        else:
            regime = "normal"

        return VolatilityReading(
            realized_vol=realized,
            short_vol=short_vol,
            long_vol=long_vol,
            vol_of_vol=vol_of_vol,
            atr_value=atr_value,
            atr_expansion=atr_expansion,
            bb_width=bb_width,
            bb_compression=compression,
            regime=regime,
        )
