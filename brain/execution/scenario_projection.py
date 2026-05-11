"""Scenario projection — probabilistic forward outlook.

Produces a structural (non-directional) projection of likely next regime,
along with structural collapse / expansion / continuation probabilities.
This is *not* a price forecast — it is a forecast over structural states.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from brain.math_core import clamp
from brain.schemas import DiagnosisLabel, RegimeLabel, StandardizedDiagnosis


@dataclass
class StructuralProjection:
    next_regime_probabilities: Dict[str, float]
    collapse_probability: float
    expansion_probability: float
    continuation_probability: float
    transition_probability: float
    horizon_bars: int
    rationale: str


class ScenarioProjection:
    def project(self, diag: StandardizedDiagnosis, horizon_bars: int = 20) -> StructuralProjection:
        ps = diag.pathology_scores
        regime = diag.regime

        pre_collapse = ps.pre_collapse
        compression_release = ps.compression_pressure
        stress = ps.stress_escalation
        instability = ps.structural_instability
        continuation_failure = ps.continuation_failure

        collapse_prob = clamp(
            0.45 * pre_collapse + 0.25 * stress + 0.15 * instability + 0.15 * continuation_failure,
            0.0, 1.0,
        )
        expansion_prob = clamp(
            0.55 * compression_release
            + 0.20 * (1.0 - stress)
            + 0.15 * (1.0 - instability)
            + 0.10 * (1.0 - continuation_failure),
            0.0, 1.0,
        )
        continuation_prob = clamp(
            0.40 * (1.0 - ps.continuation_failure)
            + 0.30 * (1.0 - ps.hidden_exhaustion)
            + 0.30 * (1.0 - instability),
            0.0, 1.0,
        )
        transition_prob = clamp(
            0.50 * instability + 0.30 * stress + 0.20 * ps.entropy_disorder, 0.0, 1.0,
        )

        # Next regime probability vector.
        regime_probs = {
            RegimeLabel.CHAOTIC.value: clamp(0.6 * instability + 0.4 * ps.entropy_disorder, 0.0, 1.0),
            RegimeLabel.EXPANSION.value: clamp(0.7 * expansion_prob + 0.2 * (1.0 - stress), 0.0, 1.0),
            RegimeLabel.COMPRESSION.value: clamp(0.7 * (1.0 - expansion_prob) + 0.3 * (1.0 - stress), 0.0, 1.0),
            RegimeLabel.TREND_UP.value: clamp(0.6 * continuation_prob + 0.4 * (1.0 - instability), 0.0, 1.0),
            RegimeLabel.TREND_DOWN.value: clamp(0.6 * continuation_prob + 0.4 * (1.0 - instability), 0.0, 1.0),
            RegimeLabel.MEAN_REVERSION.value: clamp(0.5 * ps.acceptance_failure + 0.5 * (1.0 - continuation_prob), 0.0, 1.0),
        }
        total = sum(regime_probs.values()) or 1e-9
        regime_probs = {k: v / total for k, v in regime_probs.items()}

        rationale = (
            f"Projection horizon: {horizon_bars} bars. Collapse={collapse_prob:.2f}, "
            f"Expansion={expansion_prob:.2f}, Continuation={continuation_prob:.2f}, "
            f"Transition={transition_prob:.2f}. Dominant pathology contributor: "
            f"{max(ps.as_dict().items(), key=lambda kv: kv[1])[0]}."
        )

        return StructuralProjection(
            next_regime_probabilities=regime_probs,
            collapse_probability=collapse_prob,
            expansion_probability=expansion_prob,
            continuation_probability=continuation_prob,
            transition_probability=transition_prob,
            horizon_bars=int(horizon_bars),
            rationale=rationale,
        )
