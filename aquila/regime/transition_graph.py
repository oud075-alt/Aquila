"""Regime transition graph — a transparent probabilistic transition matrix
over `RegimeState` snapshots.
"""

from __future__ import annotations

from collections import defaultdict

from aquila.regime.schemas import RegimeState, RegimeTransition


class RegimeTransitionGraph:
    def __init__(self) -> None:
        self._counts: dict[tuple, dict[tuple, int]] = defaultdict(lambda: defaultdict(int))
        self._totals: dict[tuple, int] = defaultdict(int)

    @staticmethod
    def _key(s: RegimeState) -> tuple:
        return (s.volatility.value, s.liquidity.value, s.participation.value)

    def observe(self, prev: RegimeState, curr: RegimeState) -> None:
        pk, ck = self._key(prev), self._key(curr)
        self._counts[pk][ck] += 1
        self._totals[pk] += 1

    def transition_probability(self, prev: RegimeState, curr: RegimeState) -> float:
        pk, ck = self._key(prev), self._key(curr)
        total = self._totals.get(pk, 0)
        if total == 0:
            return 0.0
        return self._counts[pk].get(ck, 0) / total

    def explain(self, prev: RegimeState, curr: RegimeState) -> RegimeTransition:
        prob = self.transition_probability(prev, curr)
        rationale = "observed" if prob > 0 else "novel"
        return RegimeTransition(from_state=prev, to_state=curr, probability=prob, rationale=rationale)
