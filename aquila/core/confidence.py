"""Confidence calculus — weighted-mean propagation rules used across
layers. Closes audit gap #10 (no confidence-propagation formalism).

We deliberately keep this simple, transparent, and replayable. No hidden
math, no learned priors. All operations are pure functions.
"""

from __future__ import annotations

from math import prod

from aquila.core.numeric import safe_prob


class ConfidenceCalculus:
    @staticmethod
    def combine_independent(values: list[float]) -> float:
        """Probabilistic OR of independent supporting evidence:
        c = 1 - prod(1 - c_i)
        """
        if not values:
            return 0.0
        clamped = [safe_prob(v) for v in values]
        return safe_prob(1.0 - prod(1.0 - v for v in clamped))

    @staticmethod
    def conjunction(values: list[float]) -> float:
        """Probabilistic AND: c = prod(c_i)."""
        if not values:
            return 0.0
        return safe_prob(prod(safe_prob(v) for v in values))

    @staticmethod
    def decay(value: float, age_steps: int, half_life: int = 10) -> float:
        """Exponential confidence decay over discrete steps."""
        if half_life <= 0:
            return safe_prob(value)
        factor = 0.5 ** (age_steps / half_life)
        return safe_prob(safe_prob(value) * factor)

    @staticmethod
    def weighted_mean(pairs: list[tuple[float, float]]) -> float:
        """pairs = [(weight, confidence), ...]"""
        if not pairs:
            return 0.0
        total_w = sum(max(0.0, w) for w, _ in pairs)
        if total_w == 0.0:
            return 0.0
        s = sum(max(0.0, w) * safe_prob(c) for w, c in pairs)
        return safe_prob(s / total_w)

    @staticmethod
    def contradiction_penalty(confidence: float, contradiction_score: float) -> float:
        """Reduce confidence proportionally to contradiction."""
        return safe_prob(safe_prob(confidence) * (1.0 - safe_prob(contradiction_score)))
