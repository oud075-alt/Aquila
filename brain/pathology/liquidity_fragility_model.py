"""Liquidity fragility model.

Combines liquidity-map vacuum, sweep risk and orderflow imbalance to
estimate the probability that small flows can cause disproportionate
moves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from brain.math_core import clamp, safe_div
from brain.schemas import Candle
from brain.sensory.liquidity_map import LiquidityMap, LiquidityProfile
from brain.sensory.orderflow_parser import OrderflowMetrics


@dataclass
class LiquidityFragilityAssessment:
    score: float
    profile: LiquidityProfile
    features: Dict[str, float]


class LiquidityFragilityModel:
    def __init__(self):
        self.map = LiquidityMap()

    def evaluate(
        self,
        candles: List[Candle],
        orderflow: OrderflowMetrics,
    ) -> LiquidityFragilityAssessment:
        if len(candles) < 50:
            return LiquidityFragilityAssessment(0.0, LiquidityMap().build(candles), {})

        profile = self.map.build(candles)
        ranges = np.array([c.range for c in candles[-50:]], dtype=np.float64)
        volumes = np.array([c.volume for c in candles[-50:]], dtype=np.float64)
        rng_z = (ranges - ranges.mean()) / (ranges.std() + 1e-9)
        vol_z = (volumes - volumes.mean()) / (volumes.std() + 1e-9)
        thin_move = float(np.mean(np.maximum(0.0, rng_z[-10:] - vol_z[-10:])))
        thin_move = clamp(thin_move / 2.0, 0.0, 1.0)

        score = clamp(
            0.30 * profile.vacuum_score
            + 0.30 * profile.sweep_risk
            + 0.20 * thin_move
            + 0.10 * abs(profile.imbalance)
            + 0.10 * orderflow.absorption / 5.0,
            0.0,
            1.0,
        )

        features = {
            "vacuum_score": float(profile.vacuum_score),
            "sweep_risk": float(profile.sweep_risk),
            "thin_move": float(thin_move),
            "imbalance": float(profile.imbalance),
            "absorption": float(orderflow.absorption),
        }
        return LiquidityFragilityAssessment(score=score, profile=profile, features=features)
