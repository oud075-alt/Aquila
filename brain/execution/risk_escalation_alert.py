"""Risk escalation alert.

Builds an :class:`EscalationRisk` object from the pathology bundle and
structural projection. The orchestrator merges this into the standardized
diagnosis before persistence / alerting.
"""

from __future__ import annotations

from brain.math_core import clamp
from brain.schemas import EscalationRisk, PathologyScores, StateTransition


class RiskEscalationAlert:
    def compute(
        self,
        pathology: PathologyScores,
        transition: StateTransition,
        compression_release_prob: float,
        bull_bias: float,
    ) -> EscalationRisk:
        # Short-term horizon dominated by stress & liquidity fragility
        short = clamp(
            0.45 * pathology.stress_escalation
            + 0.30 * pathology.liquidity_fragility
            + 0.25 * pathology.behavioral_divergence,
            0.0,
            1.0,
        )
        # Medium-term horizon weighted by exhaustion + acceptance failure + instability
        medium = clamp(
            0.40 * pathology.hidden_exhaustion
            + 0.30 * pathology.acceptance_failure
            + 0.30 * pathology.structural_instability,
            0.0,
            1.0,
        )
        # Long-term horizon = composite + continuation failure + compression
        long_term = clamp(
            0.35 * pathology.continuation_failure
            + 0.30 * pathology.compression_pressure
            + 0.35 * pathology.pre_collapse,
            0.0,
            1.0,
        )

        # Direction bias from pathology composition
        if pathology.pre_collapse > 0.55 and bull_bias >= 0:
            direction = "COLLAPSE_BIAS"
        elif compression_release_prob > 0.6 and pathology.compression_pressure > 0.5:
            direction = "EXPANSION_BIAS"
        elif pathology.pre_collapse > pathology.compression_pressure:
            direction = "COLLAPSE_BIAS"
        else:
            direction = "NEUTRAL"

        pressure_build_rate = clamp(
            0.6 * transition.transition_probability
            + 0.4 * pathology.stress_escalation,
            0.0,
            1.0,
        )

        return EscalationRisk(
            short_term=short,
            medium_term=medium,
            long_term=long_term,
            direction=direction,
            pressure_build_rate=pressure_build_rate,
        )
