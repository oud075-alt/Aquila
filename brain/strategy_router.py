"""Phase 3 — Strategy Intelligence Router.

Classifies the structural environment and adjusts the DecisionPayload's
behavioral mode based on pathology + regime + risk. NOT a trading signal
engine. Outputs structural behavior categories.

Inputs: MarketState, PathologyReport, RegimeState, prior DecisionPayload, RiskState.
Outputs: DecisionPayload (mutated structural_environment, recommended_behavior,
         participation_bias, avoidance_bias, execution_safety).
"""

from __future__ import annotations

from core.pathology.metrics import clip01
from core.schemas.diagnosis_envelope import DecisionPayload
from core.schemas.enums import Regime, RiskBand, StrategyEnvironment, StructuralState
from core.schemas.market_state import MarketState
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState
from core.schemas.risk_state import RiskState


class StrategyRouter:
    """Phase 3 — structural environment router."""

    async def route(
        self,
        state: MarketState,
        pathology: PathologyReport,
        regime: RegimeState,
        decision: DecisionPayload,
        risk: RiskState,
    ) -> DecisionPayload:
        env = self._classify_environment(pathology, regime, risk)
        behavior = self._recommend_behavior(env, pathology, regime, risk)
        participation_bias, avoidance_bias = self._participation(env, decision, risk)
        execution_safety = self._execution_safety(env, pathology, risk)
        avoid = self._refine_avoidance(decision.avoid_conditions, env, regime)

        return decision.model_copy(
            update={
                "structural_environment": env,
                "recommended_behavior": behavior,
                "participation_bias": participation_bias,
                "avoidance_bias": avoidance_bias,
                "execution_safety": execution_safety,
                "avoid_conditions": avoid,
            }
        )

    def _classify_environment(
        self,
        pathology: PathologyReport,
        regime: RegimeState,
        risk: RiskState,
    ) -> StrategyEnvironment:
        if risk.risk_band == RiskBand.CRITICAL or regime.regime == Regime.DEFENSIVE:
            return StrategyEnvironment.DEFENSIVE
        if regime.regime == Regime.ENTROPIC or pathology.scores.entropy_instability >= 0.80:
            return StrategyEnvironment.HIGH_ENTROPY
        if regime.regime in (
            Regime.COMPRESSION_HEALTHY,
            Regime.COMPRESSION_UNSTABLE,
        ) or pathology.structural_state == StructuralState.COMPRESSION:
            return StrategyEnvironment.COMPRESSION
        if regime.regime == Regime.MEAN_REVERSION:
            return StrategyEnvironment.MEAN_REVERSION
        if regime.regime == Regime.TREND_HEALTHY and pathology.scores.continuation_decay < 0.45:
            return StrategyEnvironment.TREND_CONTINUATION
        if pathology.instability_score >= 0.6 or regime.regime in (
            Regime.TREND_FRAGILE,
            Regime.EXPANSION_UNSTABLE,
            Regime.COMPRESSION_UNSTABLE,
            Regime.TRANSITIONAL,
            Regime.LIQUIDITY_VACUUM,
        ):
            return StrategyEnvironment.UNSTABLE
        return StrategyEnvironment.MEAN_REVERSION

    def _recommend_behavior(
        self,
        env: StrategyEnvironment,
        pathology: PathologyReport,
        regime: RegimeState,
        risk: RiskState,
    ) -> str:
        match env:
            case StrategyEnvironment.TREND_CONTINUATION:
                return "track_structural_continuation_with_health_monitoring"
            case StrategyEnvironment.MEAN_REVERSION:
                return "monitor_oscillation_band_for_resolution"
            case StrategyEnvironment.COMPRESSION:
                return (
                    "compression_release_watch"
                    if pathology.instability_score < 0.5
                    else "fragile_compression_observation"
                )
            case StrategyEnvironment.DEFENSIVE:
                return "reduce_participation_pending_structural_resolution"
            case StrategyEnvironment.UNSTABLE:
                return "structural_instability_observation"
            case StrategyEnvironment.HIGH_ENTROPY:
                return "wait_for_entropy_collapse_before_engagement"
            case _:
                return "observe_structural_evolution"

    def _participation(
        self,
        env: StrategyEnvironment,
        decision: DecisionPayload,
        risk: RiskState,
    ) -> tuple[float, float]:
        if env in (StrategyEnvironment.DEFENSIVE, StrategyEnvironment.HIGH_ENTROPY):
            return 0.0, 1.0
        if env == StrategyEnvironment.UNSTABLE:
            return clip01(decision.participation_bias * 0.25), clip01(
                max(decision.avoidance_bias, 1.0 - risk.participation_safety)
            )
        if env == StrategyEnvironment.TREND_CONTINUATION:
            return clip01(decision.participation_bias + 0.2), clip01(decision.avoidance_bias * 0.5)
        if env == StrategyEnvironment.COMPRESSION:
            return clip01(decision.participation_bias * 0.5), clip01(decision.avoidance_bias)
        if env == StrategyEnvironment.MEAN_REVERSION:
            return clip01(decision.participation_bias * 0.6), clip01(decision.avoidance_bias)
        return decision.participation_bias, decision.avoidance_bias

    def _execution_safety(
        self,
        env: StrategyEnvironment,
        pathology: PathologyReport,
        risk: RiskState,
    ) -> float:
        base = (1.0 - pathology.instability_score) * risk.participation_safety
        match env:
            case StrategyEnvironment.DEFENSIVE | StrategyEnvironment.HIGH_ENTROPY:
                return clip01(base * 0.25)
            case StrategyEnvironment.UNSTABLE:
                return clip01(base * 0.5)
            case StrategyEnvironment.COMPRESSION:
                return clip01(base * 0.7)
            case _:
                return clip01(base)

    def _refine_avoidance(
        self,
        existing: tuple[str, ...],
        env: StrategyEnvironment,
        regime: RegimeState,
    ) -> tuple[str, ...]:
        avoid = list(existing)
        if env == StrategyEnvironment.HIGH_ENTROPY and "regime_uncertainty" not in avoid:
            avoid.append("regime_uncertainty")
        if env == StrategyEnvironment.DEFENSIVE and "structural_disorder" not in avoid:
            avoid.append("structural_disorder")
        if env == StrategyEnvironment.UNSTABLE and "instability_pressure" not in avoid:
            avoid.append("instability_pressure")
        if regime.regime == Regime.LIQUIDITY_VACUUM and "liquidity_vacuum" not in avoid:
            avoid.append("liquidity_vacuum")
        return tuple(avoid)
