"""Liquidity map — derives liquidity zones and pressure imbalance.

The map uses recent swing highs / lows + volume-weighted price density to
approximate where resting liquidity concentrates. This is consumed by the
liquidity fragility and pre-collapse pathology models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from brain.schemas import Candle


@dataclass
class LiquidityZone:
    price: float
    intensity: float        # in [0,1]
    side: str               # "above" | "below"
    distance: float         # absolute distance from current price


@dataclass
class LiquidityProfile:
    current_price: float
    zones_above: List[LiquidityZone] = field(default_factory=list)
    zones_below: List[LiquidityZone] = field(default_factory=list)
    pressure_above: float = 0.0
    pressure_below: float = 0.0
    imbalance: float = 0.0
    sweep_risk: float = 0.0
    vacuum_score: float = 0.0      # local volume vacuum 0–1

    def to_dict(self) -> Dict[str, object]:
        return {
            "current_price": self.current_price,
            "zones_above": [z.__dict__ for z in self.zones_above],
            "zones_below": [z.__dict__ for z in self.zones_below],
            "pressure_above": self.pressure_above,
            "pressure_below": self.pressure_below,
            "imbalance": self.imbalance,
            "sweep_risk": self.sweep_risk,
            "vacuum_score": self.vacuum_score,
        }


class LiquidityMap:
    """Builds a :class:`LiquidityProfile` from OHLCV history."""

    def __init__(self, lookback: int = 200, n_zones: int = 5):
        self.lookback = lookback
        self.n_zones = n_zones

    def build(self, candles: List[Candle]) -> LiquidityProfile:
        if len(candles) < 30:
            last = candles[-1].close if candles else 0.0
            return LiquidityProfile(current_price=float(last))

        recent = candles[-self.lookback:]
        highs = np.array([c.high for c in recent])
        lows = np.array([c.low for c in recent])
        volumes = np.array([c.volume for c in recent])
        last_price = float(recent[-1].close)

        # Pivot detection (3-bar fractals)
        swing_highs: List[float] = []
        swing_lows: List[float] = []
        for i in range(2, len(recent) - 2):
            window_h = highs[i - 2 : i + 3]
            window_l = lows[i - 2 : i + 3]
            if highs[i] == max(window_h):
                swing_highs.append(highs[i])
            if lows[i] == min(window_l):
                swing_lows.append(lows[i])

        def _zones(prices: List[float], side: str) -> List[LiquidityZone]:
            if not prices:
                return []
            arr = np.array(prices)
            mean_vol = float(np.mean(volumes)) or 1e-9
            # Cluster nearby pivots
            arr_sorted = np.sort(arr)
            clusters: List[List[float]] = []
            tol = float(np.std(arr_sorted)) * 0.25 + 1e-9
            current = [float(arr_sorted[0])]
            for p in arr_sorted[1:]:
                if abs(p - current[-1]) <= tol:
                    current.append(float(p))
                else:
                    clusters.append(current)
                    current = [float(p)]
            clusters.append(current)
            zones = []
            for cl in clusters:
                price = float(np.mean(cl))
                intensity = min(1.0, len(cl) / 6.0)
                zones.append(
                    LiquidityZone(
                        price=price,
                        intensity=intensity,
                        side=side,
                        distance=abs(price - last_price),
                    )
                )
            zones.sort(key=lambda z: z.distance)
            return zones[: self.n_zones]

        zones_above = _zones([p for p in swing_highs if p > last_price], "above")
        zones_below = _zones([p for p in swing_lows if p < last_price], "below")

        pressure_above = float(sum(z.intensity for z in zones_above))
        pressure_below = float(sum(z.intensity for z in zones_below))
        denom = pressure_above + pressure_below
        imbalance = float((pressure_above - pressure_below) / denom) if denom > 1e-9 else 0.0

        # Volume vacuum: large move with shrinking volume
        rng = (highs - lows)
        rng_z = (rng - np.mean(rng)) / (np.std(rng) + 1e-9)
        vol_z = (volumes - np.mean(volumes)) / (np.std(volumes) + 1e-9)
        vacuum = float(np.mean(np.maximum(0.0, rng_z[-20:] - vol_z[-20:])))
        vacuum = float(min(1.0, max(0.0, vacuum / 2.0)))

        # Sweep risk: nearest zone proximity weighted by intensity
        nearest = min(
            (zones_above[0] if zones_above else None,
             zones_below[0] if zones_below else None),
            key=lambda z: (z.distance if z else 1e18),
        )
        sweep_risk = 0.0
        if nearest is not None:
            atr_proxy = float(np.mean(rng[-20:])) or 1e-9
            proximity = max(0.0, 1.0 - nearest.distance / (atr_proxy * 3.0))
            sweep_risk = float(min(1.0, proximity * (0.4 + 0.6 * nearest.intensity)))

        return LiquidityProfile(
            current_price=last_price,
            zones_above=zones_above,
            zones_below=zones_below,
            pressure_above=pressure_above,
            pressure_below=pressure_below,
            imbalance=imbalance,
            sweep_risk=sweep_risk,
            vacuum_score=vacuum,
        )
