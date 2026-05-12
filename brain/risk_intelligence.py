"""Phase 4 — Risk Intelligence System.

Evaluates systemic structural risk by combining:

    - pathology escalation risk
    - instability severity
    - structural fragility
    - entropy escalation
    - continuation reliability
    - volatility disorder
    - liquidity collapse risk

Outputs a deterministic RiskState. Risk values emerge from real structural
conditions — no arbitrary constants beyond explicit weights.
"""

from __future__ import annotations

from collections import deque

from core.pathology.metrics import clip01
from core.schemas.contradiction_report import ContradictionReport
from core.schemas.enums import Regime, RiskBand
from core.schemas.market_state import MarketState
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState
from core.schemas.risk_state import RiskState

FRAGILITY_WEIGHT_LIQUIDITY: float = 0.4
FRAGILITY_WEIGHT_DISPERSION: float = 0.3
FRAGILITY_WEIGHT_VOLATILITY: float = 0.3

COLLAPSE_WEIGHT_ESCALATION: float = 0.4
COLLAPSE_WEIGHT_AGGREGATE: float = 0.3
COLLAPSE_WEIGHT_FRAGILITY: float = 0.3

DEFENSIVE_REGIMES: frozenset[Regime] = frozenset(
    {Regime.DEFENSIVE, Regime.ENTROPIC, Regime.LIQUIDITY_VACUUM}
)
UNSTABLE_REGIMES: frozenset[Regime] = frozenset(
    {
        Regime.TREND_FRAGILE,
        Regime.COMPRESSION_UNSTABLE,
        Regime.EXPANSION_UNSTABLE,
        Regime.TRANSITIONAL,
    }
)


class RiskIntelligenceEngine:
    """Deterministic systemic-risk synthesizer."""

    def __init__(self, *, escalation_memory: int = 32) -> None:
        self._aggregate_history: deque[float] = deque(maxlen=escalation_memory)
        self._escalation_history: deque[float] = deque(maxlen=escalation_memory)

    async def evaluate(
        self,
        state: MarketState,
        pathology: PathologyReport,
        regime: RegimeState,
        contradiction: ContradictionReport,
    ) -> RiskState:
        return self._evaluate_sync(state, pathology, regime, contradiction)

    def _evaluate_sync(
        self,
        state: MarketState,
        pathology: PathologyReport,
        regime: RegimeState,
        contradiction: ContradictionReport,
    ) -> RiskState:
        s = pathology.scores
        aggregate = s.aggregate
        escalation = pathology.escalation_risk
        instability = pathology.instability_score

        self._aggregate_history.append(aggregate)
        self._escalation_history.append(escalation)

        fragility = clip01(
            FRAGILITY_WEIGHT_LIQUIDITY * s.liquidity_imbalance
            + FRAGILITY_WEIGHT_DISPERSION * s.dispersion_shock
            + FRAGILITY_WEIGHT_VOLATILITY * s.volatility_disorder
        )

        collapse_probability = clip01(
            COLLAPSE_WEIGHT_ESCALATION * escalation
            + COLLAPSE_WEIGHT_AGGREGATE * aggregate
            + COLLAPSE_WEIGHT_FRAGILITY * fragility
        )

        instability_probability = clip01(0.7 * instability + 0.3 * s.entropy_instability)

        continuation_reliability = clip01(1.0 - s.continuation_decay)

        defensive_modifier = clip01(
            (1.0 if regime.regime in DEFENSIVE_REGIMES else 0.0) * 1.0
            + (0.5 if regime.regime in UNSTABLE_REGIMES else 0.0)
            + 0.3 * contradiction.critical_count
            + 0.4 * contradiction.invalid_count
        )

        systemic_risk_score = clip01(
            0.35 * collapse_probability
            + 0.25 * instability_probability
            + 0.20 * fragility
            + 0.10 * (1.0 - continuation_reliability)
            + 0.10 * defensive_modifier
        )

        if systemic_risk_score >= 0.85:
            band = RiskBand.CRITICAL
        elif systemic_risk_score >= 0.65:
            band = RiskBand.HIGH
        elif systemic_risk_score >= 0.40:
            band = RiskBand.ELEVATED
        else:
            band = RiskBand.HEALTHY

        confidence_decay = clip01(0.5 * systemic_risk_score + 0.5 * contradiction.contradiction_score)
        participation_safety = clip01((1.0 - systemic_risk_score) * (1.0 - contradiction.contradiction_score))

        reasoning = (
            f"systemic_risk={systemic_risk_score:.2f}",
            f"collapse_p={collapse_probability:.2f}",
            f"instability_p={instability_probability:.2f}",
            f"fragility={fragility:.2f}",
            f"continuation_reliability={continuation_reliability:.2f}",
            f"defensive_modifier={defensive_modifier:.2f}",
            f"regime={regime.regime.value}",
            f"band={band.value}",
        )

        return RiskState(
            timestamp=pathology.timestamp,
            timeframe=pathology.timeframe,
            source=pathology.source,
            confidence=1.0 - systemic_risk_score,
            risk_band=band,
            systemic_risk_score=systemic_risk_score,
            collapse_probability=collapse_probability,
            instability_probability=instability_probability,
            defensive_risk_modifier=defensive_modifier,
            confidence_decay=confidence_decay,
            participation_safety=participation_safety,
            fragility_index=fragility,
            reasoning=reasoning,
        )
