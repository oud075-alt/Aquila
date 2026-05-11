"""Composer that turns a MarketState into a PathologyReport (Phase 0C entry point).

Aggregation rule per ADR-0004 (noisy-OR over 6 primitives).
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from core.pathology.autocorrelation_breakdown import AutocorrelationBreakdown
from core.pathology.continuation_decay import ContinuationDecay
from core.pathology.dispersion_shock import DispersionShock
from core.pathology.entropy_instability import EntropyInstability
from core.pathology.liquidity_imbalance import LiquidityImbalance
from core.pathology.metrics import EPS, clip01
from core.pathology.structural_state_classifier import StructuralStateClassifier
from core.pathology.volatility_disorder import VolatilityDisorder
from core.schemas.market_state import MarketState
from core.schemas.pathology_report import PathologyReport, PathologyScores

ESCALATION_SLOPE_WINDOW: int = 16


class PathologyEngine:
    """Compose all six pathology primitives plus the structural state classifier."""

    def __init__(self) -> None:
        self.classifier = StructuralStateClassifier()
        self.entropy = EntropyInstability(self.classifier)
        self.ac_break = AutocorrelationBreakdown()
        self.liquidity = LiquidityImbalance()
        self.dispersion = DispersionShock()
        self.vol_disorder = VolatilityDisorder()
        self.cont_decay = ContinuationDecay(self.ac_break)
        self._aggregate_history: deque[float] = deque(maxlen=ESCALATION_SLOPE_WINDOW * 4)

    def _noisy_or(self, scores: tuple[float, ...]) -> float:
        n = len(scores)
        if n == 0:
            return 0.0
        accum = 0.0
        for s in scores:
            accum += math.log(1.0 - clip01(s) + EPS)
        return clip01(1.0 - math.exp(accum / n))

    def _escalation(self, current_aggregate: float) -> float:
        self._aggregate_history.append(current_aggregate)
        history = list(self._aggregate_history)
        if len(history) < 3:
            return clip01(current_aggregate)
        seg = np.array(history[-ESCALATION_SLOPE_WINDOW:], dtype=np.float64)
        x = np.arange(len(seg), dtype=np.float64)
        x_mean = x.mean()
        y_mean = seg.mean()
        denom = float(((x - x_mean) ** 2).sum())
        slope = 0.0 if denom <= EPS else float(((x - x_mean) * (seg - y_mean)).sum() / denom)
        slope_score = 0.5 * (math.tanh(8.0 * slope) + 1.0)
        return clip01(0.5 * current_aggregate + 0.5 * slope_score)

    def compute(self, state: MarketState) -> PathologyReport:
        entropy_score, _labels = self.entropy.compute(state)
        ac_break_score = self.ac_break.compute(state)
        liquidity_score = self.liquidity.compute(state)
        dispersion_score = self.dispersion.compute(state)
        vol_disorder_score = self.vol_disorder.compute(state)
        cont_decay_score = self.cont_decay.compute(state)

        vector = (
            entropy_score,
            ac_break_score,
            liquidity_score,
            dispersion_score,
            vol_disorder_score,
            cont_decay_score,
        )
        aggregate = self._noisy_or(vector)
        structural_state = self.classifier.classify(state)
        instability_score = max(
            entropy_score, vol_disorder_score, dispersion_score, cont_decay_score
        )
        escalation_risk = self._escalation(aggregate)

        scores = PathologyScores(
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
            confidence=state.data_quality,
            entropy_instability=entropy_score,
            autocorrelation_breakdown=ac_break_score,
            liquidity_imbalance=liquidity_score,
            dispersion_shock=dispersion_score,
            volatility_disorder=vol_disorder_score,
            continuation_decay=cont_decay_score,
            aggregate=aggregate,
        )
        reasoning = self._narrate(scores, structural_state, instability_score, escalation_risk)
        return PathologyReport(
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
            confidence=state.data_quality,
            scores=scores,
            structural_state=structural_state,
            structural_health=clip01(1.0 - aggregate),
            instability_score=clip01(instability_score),
            escalation_risk=clip01(escalation_risk),
            reasoning=reasoning,
        )

    def _narrate(
        self,
        scores: PathologyScores,
        state_label: str,
        instability: float,
        escalation: float,
    ) -> tuple[str, ...]:
        notes: list[str] = [f"structural_state={state_label}"]
        named = [
            ("entropy", scores.entropy_instability),
            ("autocorr_break", scores.autocorrelation_breakdown),
            ("liquidity", scores.liquidity_imbalance),
            ("dispersion", scores.dispersion_shock),
            ("vol_disorder", scores.volatility_disorder),
            ("cont_decay", scores.continuation_decay),
        ]
        named.sort(key=lambda kv: kv[1], reverse=True)
        top = named[:2]
        notes.append(f"top_drivers={','.join(f'{k}:{v:.2f}' for k,v in top)}")
        notes.append(f"aggregate={scores.aggregate:.2f}")
        notes.append(f"instability={instability:.2f}")
        notes.append(f"escalation={escalation:.2f}")
        return tuple(notes)
