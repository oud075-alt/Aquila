"""Anomaly detector.

Computes the core ANOMALY = EXPECTED - ACTUAL deviations and translates
them into normalised pathology probability components. Other pathology
models consume these components; the contradiction engine consumes both
the raw deviations and the per-feature anomaly probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from brain.math_core import abs_logistic, clamp, logistic, safe_div
from brain.schemas import ActualBehaviorProfile, ExpectationProfile


@dataclass
class AnomalyResult:
    deviations: Dict[str, float]
    probabilities: Dict[str, float]
    aggregate: float


class AnomalyDetector:
    """Compute structured anomaly probabilities between expected and actual."""

    def __init__(self, sensitivity: float = 1.8):
        # ``sensitivity`` scales the logistic slope (higher = more sensitive).
        self.sensitivity = sensitivity

    def evaluate(self, expected: ExpectationProfile, actual: ActualBehaviorProfile) -> AnomalyResult:
        # Each deviation is normalised either as a relative ratio (when the
        # expectation magnitude is meaningful) or as a signed difference
        # for unit-less quantities.
        eps = 1e-9

        def rel(a: float, e: float) -> float:
            return safe_div(a - e, abs(e) + eps, default=0.0)

        deviations = {
            "slope": rel(actual.realized_trend_slope, expected.expected_trend_slope),
            "persistence": float(actual.realized_continuation_persistence - expected.expected_continuation_persistence),
            "volatility": rel(actual.realized_volatility, expected.expected_volatility),
            "atr": rel(actual.realized_atr, expected.expected_atr),
            "participation": rel(actual.realized_participation, expected.expected_participation),
            "acceptance": float(actual.realized_acceptance - expected.expected_acceptance),
            "efficiency": float(actual.realized_efficiency - expected.expected_efficiency),
            "followthrough": float(actual.realized_breakout_followthrough - expected.expected_breakout_followthrough),
            "compression_release": rel(
                actual.realized_compression_release_ratio,
                expected.expected_compression_release_ratio,
            ),
        }

        # Convert each deviation to a probability of pathology. Negative
        # deviations (actual<expected) for "good" metrics are treated as
        # pathological; positive deviations are pathological for "stress"
        # metrics (vol, atr, compression release).
        probabilities = {
            # When realised slope is far below expected (or opposite sign):
            "slope": abs_logistic(deviations["slope"], k=self.sensitivity * 2.0),
            # Persistence deficit (negative is bad):
            "persistence": abs_logistic(-deviations["persistence"], k=self.sensitivity * 4.0),
            # Volatility above expected = stress; below expected = compression
            # We treat the *magnitude* as anomaly:
            "volatility": abs_logistic(deviations["volatility"], k=self.sensitivity * 1.2),
            "atr": abs_logistic(deviations["atr"], k=self.sensitivity * 1.5),
            # Participation deficit during expansion is pathological:
            "participation": abs_logistic(-deviations["participation"], k=self.sensitivity * 1.8),
            # Acceptance deficit is pathological:
            "acceptance": abs_logistic(-deviations["acceptance"], k=self.sensitivity * 4.0),
            "efficiency": abs_logistic(-deviations["efficiency"], k=self.sensitivity * 3.0),
            # Follow-through below expected is pathological:
            "followthrough": abs_logistic(-deviations["followthrough"], k=self.sensitivity * 2.5),
            "compression_release": abs_logistic(
                deviations["compression_release"], k=self.sensitivity * 1.5
            ),
        }

        # Aggregate via probability OR
        prob = 1.0
        for v in probabilities.values():
            prob *= (1.0 - clamp(v, 0.0, 1.0))
        aggregate = clamp(1.0 - prob, 0.0, 1.0)

        return AnomalyResult(deviations=deviations, probabilities=probabilities, aggregate=aggregate)
