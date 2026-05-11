"""Phase 1 — Decision Engine.

Transforms pathology + regime + contradiction state into a DecisionPayload of
STRUCTURAL INTELLIGENCE actions (not trading signals).

Anti-drift contract:
    - No `direction`, `entry_price`, `exit_price`, `stop_loss`, `take_profit`,
      `position_size`, `buy`, `sell`, `long`, `short`, `trade_signal`.
    - Outputs are cognitive labels describing the structural posture the
      system should adopt (OBSERVE_STRUCTURE / TRACK_CONTINUATION /
      MONITOR_FRAGILITY / ESCALATE_DEFENSIVE / ...).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.orchestrator.pipeline_executor import DiagnosisCoordinatorContext
from core.pathology.metrics import clip01
from core.schemas.diagnosis_envelope import DecisionPayload
from core.schemas.enums import Regime, StrategyEnvironment, StructuralState
from core.schemas.market_state import MarketState
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState

ACTION_OBSERVE = "OBSERVE_STRUCTURE"
ACTION_TRACK = "TRACK_CONTINUATION"
ACTION_MONITOR_FRAGILITY = "MONITOR_FRAGILITY"
ACTION_WATCH_EXPANSION = "WATCH_EXPANSION"
ACTION_WATCH_COMPRESSION = "WATCH_COMPRESSION"
ACTION_DETECT_TRANSITION = "DETECT_TRANSITION"
ACTION_ESCALATE_DEFENSIVE = "ESCALATE_DEFENSIVE"
ACTION_WAIT_RESOLUTION = "WAIT_RESOLUTION"

RISK_MODE_DEFAULT = "DEFAULT"
RISK_MODE_DEFENSIVE = "DEFENSIVE"
RISK_MODE_DEGRADED = "DEGRADED"
RISK_MODE_CRITICAL = "CRITICAL"

BIAS_NEUTRAL = "NEUTRAL"
BIAS_CONTINUATION = "CONTINUATION_HEALTHY"
BIAS_COMPRESSION_WATCH = "COMPRESSION_WATCH"
BIAS_REVERSAL_MONITOR = "REVERSAL_MONITOR"
BIAS_FRAGILE_OBS = "FRAGILE_OBSERVATION"
BIAS_DEFENSIVE = "DEFENSIVE_POSTURE"

STRUCT_BIAS_BALANCED = "BALANCED"
STRUCT_BIAS_TRENDING = "TRENDING"
STRUCT_BIAS_COMPRESSING = "COMPRESSING"
STRUCT_BIAS_EXPANDING = "EXPANDING"
STRUCT_BIAS_TRANSITIONING = "TRANSITIONING"
STRUCT_BIAS_COLLAPSING = "COLLAPSING"


@dataclass(frozen=True, slots=True)
class _ConfidenceModulation:
    base: float
    instability_penalty: float
    entropy_penalty: float
    defensive_penalty: float

    @property
    def final(self) -> float:
        return clip01(
            self.base * (1.0 - self.instability_penalty) * (1.0 - self.entropy_penalty) * (1.0 - self.defensive_penalty)
        )


class DecisionEngine:
    """Deterministic decision engine — Phase 1."""

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

    async def decide(
        self,
        state: MarketState,
        pathology: PathologyReport,
        regime: RegimeState,
        _ctx: DiagnosisCoordinatorContext,
    ) -> DecisionPayload:
        return self._decide_sync(state, pathology, regime)

    def _decide_sync(
        self,
        state: MarketState,
        pathology: PathologyReport,
        regime: RegimeState,
    ) -> DecisionPayload:
        s = pathology.scores
        instability = pathology.instability_score
        escalation = pathology.escalation_risk
        aggregate = s.aggregate
        structural_state = pathology.structural_state

        is_defensive = regime.regime in self.DEFENSIVE_REGIMES
        is_unstable = regime.regime in self.UNSTABLE_REGIMES

        action = ACTION_OBSERVE
        risk_mode = RISK_MODE_DEFAULT
        strategy_bias = BIAS_NEUTRAL
        structural_bias = STRUCT_BIAS_BALANCED
        recommended_behavior = "observe_structural_evolution"
        env = StrategyEnvironment.UNSTABLE
        avoid: list[str] = []
        reasoning: list[str] = []
        defensive_state = is_defensive

        if escalation >= 0.85 or regime.regime == Regime.DEFENSIVE:
            action = ACTION_ESCALATE_DEFENSIVE
            risk_mode = RISK_MODE_CRITICAL if escalation >= 0.9 else RISK_MODE_DEFENSIVE
            strategy_bias = BIAS_DEFENSIVE
            structural_bias = STRUCT_BIAS_COLLAPSING
            env = StrategyEnvironment.DEFENSIVE
            recommended_behavior = "reduce_participation_pending_structural_resolution"
            avoid.extend(["high_escalation_risk", "structural_disorder"])
            reasoning.append(f"escalation={escalation:.2f} forces defensive escalation")
            defensive_state = True
        elif regime.regime == Regime.ENTROPIC or s.entropy_instability >= 0.80:
            action = ACTION_WAIT_RESOLUTION
            risk_mode = RISK_MODE_DEFENSIVE
            strategy_bias = BIAS_FRAGILE_OBS
            structural_bias = STRUCT_BIAS_TRANSITIONING
            env = StrategyEnvironment.HIGH_ENTROPY
            recommended_behavior = "wait_for_entropy_collapse"
            avoid.extend(["high_entropy", "regime_uncertainty"])
            reasoning.append("entropy escalation; structural alphabet is dispersed")
            defensive_state = True
        elif regime.regime == Regime.LIQUIDITY_VACUUM or s.liquidity_imbalance >= 0.80:
            action = ACTION_MONITOR_FRAGILITY
            risk_mode = RISK_MODE_DEFENSIVE
            strategy_bias = BIAS_FRAGILE_OBS
            structural_bias = STRUCT_BIAS_COLLAPSING
            env = StrategyEnvironment.DEFENSIVE
            recommended_behavior = "monitor_liquidity_recovery"
            avoid.extend(["liquidity_vacuum", "spread_widening"])
            reasoning.append("liquidity fragility dominant")
            defensive_state = True
        elif structural_state == StructuralState.REVERSAL_PRESSURE and instability >= 0.5:
            action = ACTION_DETECT_TRANSITION
            risk_mode = RISK_MODE_DEFENSIVE
            strategy_bias = BIAS_REVERSAL_MONITOR
            structural_bias = STRUCT_BIAS_TRANSITIONING
            env = StrategyEnvironment.UNSTABLE
            recommended_behavior = "treat_as_potential_structural_inflection"
            avoid.append("continuation_assumption")
            reasoning.append("reversal pressure with elevated instability")
            defensive_state = True
        elif (
            regime.regime in (Regime.TREND_HEALTHY,)
            and s.continuation_decay < 0.45
            and instability < 0.45
        ):
            action = ACTION_TRACK
            risk_mode = RISK_MODE_DEFAULT
            strategy_bias = BIAS_CONTINUATION
            structural_bias = STRUCT_BIAS_TRENDING
            env = StrategyEnvironment.TREND_CONTINUATION
            recommended_behavior = "track_structural_continuation"
            reasoning.append("healthy continuation; pathology subdued")
        elif regime.regime == Regime.TREND_FRAGILE or (
            structural_state in (StructuralState.UP_CONTINUATION, StructuralState.DOWN_CONTINUATION)
            and s.continuation_decay >= 0.55
        ):
            action = ACTION_MONITOR_FRAGILITY
            risk_mode = RISK_MODE_DEGRADED
            strategy_bias = BIAS_FRAGILE_OBS
            structural_bias = STRUCT_BIAS_TRENDING
            env = StrategyEnvironment.UNSTABLE
            recommended_behavior = "monitor_continuation_fragility"
            avoid.append("continuation_decay")
            reasoning.append("continuation decay rising inside trend regime")
            defensive_state = is_unstable
        elif regime.regime == Regime.COMPRESSION_HEALTHY:
            action = ACTION_WATCH_COMPRESSION
            risk_mode = RISK_MODE_DEFAULT
            strategy_bias = BIAS_COMPRESSION_WATCH
            structural_bias = STRUCT_BIAS_COMPRESSING
            env = StrategyEnvironment.COMPRESSION
            recommended_behavior = "watch_for_expansion_release"
            reasoning.append("healthy compression; structural energy accumulating")
        elif regime.regime == Regime.COMPRESSION_UNSTABLE:
            action = ACTION_MONITOR_FRAGILITY
            risk_mode = RISK_MODE_DEGRADED
            strategy_bias = BIAS_COMPRESSION_WATCH
            structural_bias = STRUCT_BIAS_COMPRESSING
            env = StrategyEnvironment.UNSTABLE
            recommended_behavior = "compression_with_pathology_pressure"
            avoid.append("false_expansion")
            reasoning.append("compression with pathology pressure → fragile release risk")
            defensive_state = True
        elif regime.regime == Regime.EXPANSION_HEALTHY:
            action = ACTION_WATCH_EXPANSION
            risk_mode = RISK_MODE_DEFAULT
            strategy_bias = BIAS_NEUTRAL
            structural_bias = STRUCT_BIAS_EXPANDING
            env = StrategyEnvironment.TREND_CONTINUATION
            recommended_behavior = "monitor_expansion_sustainability"
            reasoning.append("healthy expansion; sustainability monitoring")
        elif regime.regime == Regime.EXPANSION_UNSTABLE:
            action = ACTION_MONITOR_FRAGILITY
            risk_mode = RISK_MODE_DEGRADED
            strategy_bias = BIAS_FRAGILE_OBS
            structural_bias = STRUCT_BIAS_EXPANDING
            env = StrategyEnvironment.UNSTABLE
            recommended_behavior = "unstable_expansion_alert"
            avoid.extend(["unstable_expansion", "dispersion_shock"])
            reasoning.append("expansion volatile; dispersion or volatility disorder elevated")
            defensive_state = True
        elif regime.regime == Regime.MEAN_REVERSION:
            action = ACTION_DETECT_TRANSITION
            risk_mode = RISK_MODE_DEFAULT
            strategy_bias = BIAS_REVERSAL_MONITOR
            structural_bias = STRUCT_BIAS_BALANCED
            env = StrategyEnvironment.MEAN_REVERSION
            recommended_behavior = "watch_for_oscillation_resolution"
            reasoning.append("mean-reverting structural posture")
        elif regime.regime == Regime.TRANSITIONAL:
            action = ACTION_DETECT_TRANSITION
            risk_mode = RISK_MODE_DEGRADED
            strategy_bias = BIAS_NEUTRAL
            structural_bias = STRUCT_BIAS_TRANSITIONING
            env = StrategyEnvironment.UNSTABLE
            recommended_behavior = "await_regime_resolution"
            avoid.append("premature_regime_assumption")
            reasoning.append("transitional regime — directionality undefined")

        if aggregate >= 0.65 and "high_pathology_aggregate" not in avoid:
            avoid.append("high_pathology_aggregate")
        if s.continuation_decay >= 0.70 and "continuation_decay" not in avoid:
            avoid.append("continuation_decay")
        if s.dispersion_shock >= 0.70 and "dispersion_shock" not in avoid:
            avoid.append("dispersion_shock")
        if s.volatility_disorder >= 0.70 and "volatility_disorder" not in avoid:
            avoid.append("volatility_disorder")

        confidence_mod = _ConfidenceModulation(
            base=pathology.structural_health,
            instability_penalty=clip01(instability) * 0.5,
            entropy_penalty=clip01(s.entropy_instability) * 0.4,
            defensive_penalty=0.4 if defensive_state else 0.0,
        )
        confidence_value = confidence_mod.final

        execution_safety = clip01((1.0 - instability) * (1.0 - s.dispersion_shock))
        participation_bias = 0.0 if defensive_state else clip01(
            pathology.structural_health * (1.0 - aggregate)
        )
        avoidance_bias = clip01(0.5 * instability + 0.5 * aggregate)

        if defensive_state and risk_mode == RISK_MODE_DEFAULT:
            risk_mode = RISK_MODE_DEFENSIVE

        reasoning_tuple = tuple(reasoning + [
            f"regime={regime.regime.value}",
            f"structural_state={structural_state.value}",
            f"aggregate={aggregate:.2f}",
            f"instability={instability:.2f}",
            f"escalation={escalation:.2f}",
            f"confidence={confidence_value:.2f}",
        ])

        return DecisionPayload(
            timestamp=pathology.timestamp,
            timeframe=pathology.timeframe,
            source=pathology.source,
            confidence=confidence_value,
            action=action,
            risk_mode=risk_mode,
            strategy_bias=strategy_bias,
            avoid_conditions=tuple(avoid),
            structural_bias=structural_bias,
            defensive_state=defensive_state,
            structural_environment=env,
            recommended_behavior=recommended_behavior,
            execution_safety=execution_safety,
            participation_bias=participation_bias,
            avoidance_bias=avoidance_bias,
        )
