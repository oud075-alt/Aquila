"""Regime classifier — maps pathology + structural state → closed Regime enum.

Lives in the orchestrator package because regime synthesis is part of the
orchestrator's authority to *consolidate* diagnoses. The classifier is
deterministic and uses the closed enum from Appendix B.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from core.schemas.enums import Regime, StructuralState
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState

PERSISTENCE_WINDOW: int = 32


@dataclass(slots=True)
class _RegimeMemory:
    last: Regime | None = None
    persistence: int = 0
    history: deque[Regime] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = deque(maxlen=PERSISTENCE_WINDOW)

    def update(self, regime: Regime) -> tuple[int, Regime | None]:
        prev = self.last
        if prev == regime:
            self.persistence += 1
        else:
            self.persistence = 1
        self.last = regime
        self.history.append(regime)
        return self.persistence, prev


class RegimeClassifier:
    """Deterministic regime classifier (closed enum, Appendix B)."""

    def __init__(self) -> None:
        self._memory = _RegimeMemory()

    def classify(self, report: PathologyReport) -> RegimeState:
        regime = self._select_regime(report)
        persistence, previous = self._memory.update(regime)
        transition_pressure = self._transition_pressure(report)
        regime_confidence = self._regime_confidence(report, regime, persistence)

        reasoning = (
            f"structural_state={report.structural_state.value}",
            f"aggregate={report.scores.aggregate:.2f}",
            f"instability={report.instability_score:.2f}",
            f"escalation={report.escalation_risk:.2f}",
            f"persistence={persistence}",
        )
        return RegimeState(
            timestamp=report.timestamp,
            timeframe=report.timeframe,
            source=report.source,
            confidence=regime_confidence,
            regime=regime,
            regime_confidence=regime_confidence,
            regime_persistence_bars=persistence,
            transition_pressure=transition_pressure,
            previous_regime=previous,
            reasoning=reasoning,
        )

    def _select_regime(self, r: PathologyReport) -> Regime:
        s = r.scores
        st = r.structural_state
        aggregate = s.aggregate
        instability = r.instability_score
        escalation = r.escalation_risk

        if aggregate >= 0.85 or escalation >= 0.85:
            if s.entropy_instability >= 0.70:
                return Regime.ENTROPIC
            return Regime.DEFENSIVE

        if st == StructuralState.REVERSAL_PRESSURE and instability >= 0.5:
            return Regime.DEFENSIVE

        if st == StructuralState.LIQUIDITY_STALL:
            return Regime.LIQUIDITY_VACUUM

        if st == StructuralState.VOLATILITY_EXPANSION:
            return Regime.EXPANSION_UNSTABLE if instability >= 0.5 else Regime.EXPANSION_HEALTHY

        if st == StructuralState.COMPRESSION:
            return Regime.COMPRESSION_UNSTABLE if instability >= 0.5 else Regime.COMPRESSION_HEALTHY

        if st in (StructuralState.UP_CONTINUATION, StructuralState.DOWN_CONTINUATION):
            decay = s.continuation_decay
            if decay >= 0.6 or instability >= 0.6:
                return Regime.TREND_FRAGILE
            return Regime.TREND_HEALTHY

        if st == StructuralState.CHAOTIC_TRANSITION:
            if instability >= 0.55:
                return Regime.ENTROPIC
            if s.dispersion_shock >= 0.6:
                return Regime.TRANSITIONAL
            return Regime.MEAN_REVERSION

        return Regime.TRANSITIONAL

    def _transition_pressure(self, r: PathologyReport) -> float:
        s = r.scores
        return max(0.0, min(1.0, 0.5 * s.dispersion_shock + 0.5 * s.entropy_instability))

    def _regime_confidence(self, r: PathologyReport, regime: Regime, persistence: int) -> float:
        base = max(0.0, 1.0 - r.scores.aggregate)
        persist_factor = min(1.0, persistence / 8.0)
        return max(0.0, min(1.0, 0.5 * base + 0.5 * persist_factor))
