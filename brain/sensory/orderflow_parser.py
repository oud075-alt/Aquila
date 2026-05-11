"""Order-flow parser.

Builds a compact representation of buy/sell imbalance, sweep frequency and
absorption from tick / OHLCV data. This is one of the foundational inputs
for the liquidity fragility and stress escalation pathology models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np

from brain.schemas import Candle


@dataclass
class OrderflowMetrics:
    buy_pressure: float = 0.0      # in [-1, 1]
    sell_pressure: float = 0.0
    aggressor_imbalance: float = 0.0
    sweep_count: int = 0
    sweep_frequency: float = 0.0
    absorption: float = 0.0        # ratio of large move with low traded volume
    upper_wick_ratio: float = 0.0
    lower_wick_ratio: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "buy_pressure": self.buy_pressure,
            "sell_pressure": self.sell_pressure,
            "aggressor_imbalance": self.aggressor_imbalance,
            "sweep_count": self.sweep_count,
            "sweep_frequency": self.sweep_frequency,
            "absorption": self.absorption,
            "upper_wick_ratio": self.upper_wick_ratio,
            "lower_wick_ratio": self.lower_wick_ratio,
        }


class OrderflowParser:
    """Derives orderflow-style metrics from OHLCV bars + tick events."""

    def __init__(self, sweep_z: float = 2.5):
        self.sweep_z = sweep_z

    def parse(self, candles: List[Candle], ticks: Iterable[Dict] | None = None) -> OrderflowMetrics:
        if len(candles) < 5:
            return OrderflowMetrics()

        ranges = np.array([c.range for c in candles], dtype=np.float64)
        bodies = np.array([c.body for c in candles], dtype=np.float64)
        upper = np.array([c.upper_wick for c in candles], dtype=np.float64)
        lower = np.array([c.lower_wick for c in candles], dtype=np.float64)
        volumes = np.array([c.volume for c in candles], dtype=np.float64)
        bullish = np.array([1.0 if c.is_bullish else -1.0 for c in candles])

        rng_mean = float(np.mean(ranges)) or 1e-9
        rng_std = float(np.std(ranges, ddof=1)) or 1e-9
        sweep_mask = (ranges - rng_mean) / rng_std > self.sweep_z
        sweep_count = int(np.count_nonzero(sweep_mask))
        sweep_frequency = float(sweep_count / max(1, len(candles)))

        # Buy/sell pressure from body direction weighted by volume
        body_vol = bodies * np.sign(bullish) * volumes
        denom = float(np.sum(np.abs(body_vol))) or 1e-9
        aggressor_imb = float(np.sum(body_vol) / denom)
        buy_pressure = float(np.clip(aggressor_imb, 0.0, 1.0))
        sell_pressure = float(np.clip(-aggressor_imb, 0.0, 1.0))

        # Absorption: large range with low volume ⇒ liquidity vacuum
        norm_range = ranges / (rng_mean if rng_mean > 0 else 1e-9)
        norm_vol = volumes / (float(np.mean(volumes)) or 1e-9)
        absorption_series = np.maximum(0.0, norm_range - norm_vol)
        absorption = float(np.mean(absorption_series[-20:]))

        upper_ratio_series = upper / (ranges + 1e-9)
        lower_ratio_series = lower / (ranges + 1e-9)
        upper_wick_ratio = float(np.mean(upper_ratio_series[-20:])) if upper_ratio_series.size else 0.0
        lower_wick_ratio = float(np.mean(lower_ratio_series[-20:])) if lower_ratio_series.size else 0.0

        # Refine with tick-level aggressor data when available
        if ticks:
            buy_vol = sum(float(t.get("volume", 0.0)) for t in ticks if t.get("side") == "buy")
            sell_vol = sum(float(t.get("volume", 0.0)) for t in ticks if t.get("side") == "sell")
            tot = buy_vol + sell_vol
            if tot > 0:
                aggressor_imb = float((buy_vol - sell_vol) / tot)
                buy_pressure = float(np.clip(aggressor_imb, 0.0, 1.0))
                sell_pressure = float(np.clip(-aggressor_imb, 0.0, 1.0))

        return OrderflowMetrics(
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            aggressor_imbalance=aggressor_imb,
            sweep_count=sweep_count,
            sweep_frequency=sweep_frequency,
            absorption=float(np.clip(absorption, 0.0, 5.0)),
            upper_wick_ratio=float(np.clip(upper_wick_ratio, 0.0, 1.0)),
            lower_wick_ratio=float(np.clip(lower_wick_ratio, 0.0, 1.0)),
        )
