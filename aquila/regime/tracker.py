"""Probabilistic regime tracker — exponential running weighting; transparent."""

from __future__ import annotations

from collections import defaultdict

from aquila.core.numeric import safe_prob
from aquila.regime.schemas import RegimeKind, RegimeState


class ProbabilisticRegimeTracker:
    def __init__(self, alpha: float = 0.1) -> None:
        self.alpha = max(0.01, min(1.0, alpha))
        self._vol_dist: dict[RegimeKind, float] = defaultdict(float)
        self._liq_dist: dict[RegimeKind, float] = defaultdict(float)
        self._part_dist: dict[RegimeKind, float] = defaultdict(float)

    def _update(self, dist: dict[RegimeKind, float], k: RegimeKind) -> None:
        for kk in list(dist.keys()):
            dist[kk] = (1 - self.alpha) * dist[kk]
        dist[k] = dist.get(k, 0.0) + self.alpha

    def observe(self, state: RegimeState) -> None:
        self._update(self._vol_dist, state.volatility)
        self._update(self._liq_dist, state.liquidity)
        self._update(self._part_dist, state.participation)

    def probability(self, state: RegimeState) -> float:
        return safe_prob(
            self._vol_dist.get(state.volatility, 0.0)
            * self._liq_dist.get(state.liquidity, 0.0)
            * self._part_dist.get(state.participation, 0.0)
        )
