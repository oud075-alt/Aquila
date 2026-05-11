"""Market diagnosis engine.

Coordinates every pathology model into a single :class:`PathologyScores`
result and produces all auxiliary state objects (volatility, liquidity,
continuation, instability). Consumed by the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from brain.math_core import clamp
from brain.pathology import (
    AcceptanceFailureModel,
    BehavioralDivergenceModel,
    CompressionPressureModel,
    ContinuationFailureModel,
    HiddenExhaustionModel,
    LiquidityFragilityModel,
    PreCollapseModel,
    StressEscalationModel,
    StructuralInstabilityModel,
)
from brain.pathology.anomaly_detector import AnomalyDetector
from brain.schemas import (
    ActualBehaviorProfile,
    Candle,
    ContinuationState,
    ExpectationProfile,
    InstabilityState,
    LiquidityState,
    PathologyScores,
    VolatilityState,
)
from brain.sensory.orderflow_parser import OrderflowMetrics, OrderflowParser
from brain.sensory.volatility_tracker import VolatilityTracker


@dataclass
class DiagnosisBundle:
    pathology: PathologyScores
    volatility_state: VolatilityState
    liquidity_state: LiquidityState
    continuation_state: ContinuationState
    instability_state: InstabilityState
    orderflow: OrderflowMetrics
    compression_release_prob: float
    pre_collapse_direction: str
    component_features: dict


class MarketDiagnosisEngine:
    """Runs every pathology model and aggregates their outputs."""

    def __init__(self):
        self.exhaustion_model = HiddenExhaustionModel()
        self.instability_model = StructuralInstabilityModel()
        self.continuation_failure_model = ContinuationFailureModel()
        self.liquidity_model = LiquidityFragilityModel()
        self.stress_model = StressEscalationModel()
        self.acceptance_model = AcceptanceFailureModel()
        self.divergence_model = BehavioralDivergenceModel()
        self.compression_model = CompressionPressureModel()
        self.pre_collapse_model = PreCollapseModel()
        self.anomaly_detector = AnomalyDetector()
        self.orderflow_parser = OrderflowParser()
        self.volatility_tracker = VolatilityTracker()

    def diagnose(
        self,
        candles: List[Candle],
        expected: ExpectationProfile,
        actual: ActualBehaviorProfile,
        ticks: list | None = None,
    ) -> DiagnosisBundle:
        orderflow = self.orderflow_parser.parse(candles, ticks)
        vol_reading = self.volatility_tracker.measure(candles)

        exhaustion = self.exhaustion_model.evaluate(candles)
        instability = self.instability_model.evaluate(candles)
        continuation_failure = self.continuation_failure_model.evaluate(candles, expected, actual)
        liquidity = self.liquidity_model.evaluate(candles, orderflow)
        stress = self.stress_model.evaluate(candles)
        acceptance = self.acceptance_model.evaluate(candles, expected, actual)
        divergence = self.divergence_model.evaluate(candles)
        compression = self.compression_model.evaluate(candles)

        bull_bias = float(np.sign(actual.realized_trend_slope))
        pre_collapse = self.pre_collapse_model.evaluate(
            exhaustion=exhaustion.score,
            liquidity_fragility=liquidity.score,
            stress=stress.score,
            acceptance_failure=acceptance.score,
            divergence=divergence.score,
            instability=instability.score,
            bull_bias=bull_bias,
        )

        # Manipulation footprint heuristic:
        # high sweep frequency + acceptance failure + thin participation + wick spikes
        manipulation = clamp(
            0.35 * orderflow.sweep_frequency * 4.0
            + 0.25 * acceptance.score
            + 0.20 * (1.0 - clamp(actual.realized_participation, 0.0, 1.0))
            + 0.20 * clamp(orderflow.upper_wick_ratio + orderflow.lower_wick_ratio, 0.0, 1.0),
            0.0,
            1.0,
        )

        entropy_disorder = clamp(
            0.6 * float(instability.features.get("entropy", 0.0))
            + 0.4 * (1.0 - float(instability.features.get("coherence", 0.0))),
            0.0,
            1.0,
        )

        pathology = PathologyScores(
            hidden_exhaustion=exhaustion.score,
            structural_instability=instability.score,
            continuation_failure=continuation_failure.score,
            liquidity_fragility=liquidity.score,
            stress_escalation=stress.score,
            acceptance_failure=acceptance.score,
            behavioral_divergence=divergence.score,
            pre_collapse=pre_collapse.score,
            compression_pressure=compression.score,
            manipulation_footprint=manipulation,
            entropy_disorder=entropy_disorder,
        )

        # Standardized state sub-objects.
        volatility_state = VolatilityState(
            realized_vol=vol_reading.realized_vol,
            expected_vol=expected.expected_volatility,
            vol_of_vol=vol_reading.vol_of_vol,
            compression_ratio=vol_reading.bb_compression,
            expansion_ratio=vol_reading.atr_expansion,
            label=vol_reading.regime,
        )
        liquidity_state = LiquidityState(
            participation=actual.realized_participation,
            expected_participation=expected.expected_participation,
            imbalance=liquidity.profile.imbalance,
            sweep_frequency=orderflow.sweep_frequency,
            fragility_score=liquidity.score,
            label="FRAGILE" if liquidity.score > 0.5 else "STABLE",
        )
        continuation_state = ContinuationState(
            persistence=actual.realized_continuation_persistence,
            expected_persistence=expected.expected_continuation_persistence,
            followthrough=actual.realized_breakout_followthrough,
            decay_rate=float(1.0 - actual.momentum_persistence),
            failure_probability=continuation_failure.score,
            label="FAILING" if continuation_failure.score > 0.5 else "HEALTHY",
        )
        instability_state = InstabilityState(
            rolling_std=float(actual.realized_volatility),
            entropy=float(instability.features.get("entropy", 0.0)),
            directional_coherence=float(instability.features.get("coherence", 0.0)),
            instability_score=instability.score,
            label="UNSTABLE" if instability.score > 0.55 else "STABLE",
        )

        bundle = DiagnosisBundle(
            pathology=pathology,
            volatility_state=volatility_state,
            liquidity_state=liquidity_state,
            continuation_state=continuation_state,
            instability_state=instability_state,
            orderflow=orderflow,
            compression_release_prob=compression.release_probability,
            pre_collapse_direction=pre_collapse.direction,
            component_features={
                "exhaustion": exhaustion.features,
                "instability": instability.features,
                "continuation_failure": continuation_failure.features,
                "liquidity": liquidity.features,
                "stress": stress.features,
                "acceptance": acceptance.features,
                "divergence": divergence.features,
                "compression": compression.features,
                "pre_collapse": pre_collapse.features,
            },
        )
        return bundle
