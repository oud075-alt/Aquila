"""Pipeline executor — runs the diagnosis DAG for a single MarketState.

Single-symbol Phase 0 pipeline sequence:

    ingest event
    → MarketState (via OHLCVPipeline)
    → PathologyEngine        → PathologyReport
    → RegimeClassifier       → RegimeState
    → DecisionEngine?        → DecisionPayload      (Phase 1, optional)
    → RiskEngine?            → RiskState            (Phase 4, optional)
    → ContextFusion?         → TimeframeContext     (Phase 2, optional)
    → StrategyRouter?        → DecisionPayload      (Phase 3, optional override)
    → ContradictionMatrix    → ContradictionReport
    → ConfidenceAggregator   → ConfidenceState
    → DiagnosisEnvelope (orchestrator-built)

Phase 0 ships a deterministic *default* DecisionPayload / RiskState so the
envelope is complete even before brain/* exist. Brain modules plug in via
the optional callables passed at construction.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from core.contradiction import (
    ConfidenceAggregator,
    ConsistencyValidator,
    ContradictionContext,
    ContradictionMatrix,
    PerModuleConfidence,
)
from core.orchestrator.context_manager import ContextManager
from core.orchestrator.regime_classifier import RegimeClassifier
from core.pathology import PathologyEngine
from core.schemas.confidence_state import ConfidenceState
from core.schemas.contradiction_report import ContradictionReport
from core.schemas.diagnosis_envelope import (
    DecisionPayload,
    DiagnosisEnvelope,
    DiagnosisReasoning,
)
from core.schemas.enums import (
    RiskBand,
    StrategyEnvironment,
)
from core.schemas.market_state import MarketState
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState
from core.schemas.risk_state import RiskState
from core.schemas.timeframe_context import TimeframeContext

DecisionHook = Callable[
    [MarketState, PathologyReport, RegimeState, "DiagnosisCoordinatorContext"],
    Awaitable[DecisionPayload],
]
RiskHook = Callable[
    [MarketState, PathologyReport, RegimeState, ContradictionReport],
    Awaitable[RiskState],
]
ContextHook = Callable[[ContextManager], Awaitable[TimeframeContext | None]]
RouterHook = Callable[
    [MarketState, PathologyReport, RegimeState, DecisionPayload, RiskState],
    Awaitable[DecisionPayload],
]


@dataclass(slots=True)
class DiagnosisCoordinatorContext:
    """Read-only context handed to Phase-1+ hooks for backward compatibility."""

    previous_envelope: DiagnosisEnvelope | None


class PipelineExecutor:
    """Runs the diagnosis pipeline for a single MarketState."""

    def __init__(
        self,
        *,
        context_manager: ContextManager,
        decision_hook: DecisionHook | None = None,
        risk_hook: RiskHook | None = None,
        context_fusion_hook: ContextHook | None = None,
        strategy_router_hook: RouterHook | None = None,
    ) -> None:
        self.context_manager = context_manager
        self.pathology_engine = PathologyEngine()
        self.regime_classifier = RegimeClassifier()
        self.contradiction_matrix = ContradictionMatrix()
        self.consistency_validator = ConsistencyValidator(self.contradiction_matrix)
        self.confidence_aggregator = ConfidenceAggregator()
        self.decision_hook = decision_hook
        self.risk_hook = risk_hook
        self.context_fusion_hook = context_fusion_hook
        self.strategy_router_hook = strategy_router_hook
        self._last_envelope: DiagnosisEnvelope | None = None

    async def diagnose(self, state: MarketState) -> DiagnosisEnvelope:
        pathology = self.pathology_engine.compute(state)
        regime = self.regime_classifier.classify(pathology)

        stream = self.context_manager.stream(timeframe=state.timeframe, symbol=state.symbol)
        stream.market_state = state
        stream.pathology = pathology
        stream.regime = regime

        decision_default = self._default_decision(pathology, regime)
        coordinator_ctx = DiagnosisCoordinatorContext(previous_envelope=self._last_envelope)
        decision = (
            await self.decision_hook(state, pathology, regime, coordinator_ctx)
            if self.decision_hook
            else decision_default
        )

        contradiction_pre = self._empty_contradiction(state, pathology)
        risk = (
            await self.risk_hook(state, pathology, regime, contradiction_pre)
            if self.risk_hook
            else self._default_risk(pathology, regime)
        )

        timeframe_context: TimeframeContext | None = None
        if self.context_fusion_hook is not None:
            timeframe_context = await self.context_fusion_hook(self.context_manager)

        if self.strategy_router_hook is not None:
            decision = await self.strategy_router_hook(state, pathology, regime, decision, risk)

        ctx_for_matrix = self._build_contradiction_context(
            pathology=pathology,
            regime=regime,
            decision=decision,
            timeframe_context=timeframe_context,
            pre_aggregation_confidence=state.data_quality,
        )
        validation = self.consistency_validator.validate(
            context=ctx_for_matrix,
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
            base_confidence=state.data_quality,
        )
        contradiction = validation.report

        if validation.defensive_override:
            decision = decision.model_copy(
                update={
                    "defensive_state": True,
                    "participation_bias": min(decision.participation_bias, validation.participation_ceiling),
                    "execution_safety": min(decision.execution_safety, 0.4),
                }
            )
            risk = risk.model_copy(
                update={
                    "risk_band": RiskBand.CRITICAL if validation.validation_failed else risk.risk_band,
                    "systemic_risk_score": max(risk.systemic_risk_score, validation.escalation_floor),
                    "participation_safety": min(risk.participation_safety, validation.participation_ceiling),
                }
            )

        contributors = [
            PerModuleConfidence("data_quality", state.data_quality, weight=1.0),
            PerModuleConfidence("pathology_health", pathology.structural_health, weight=1.5),
            PerModuleConfidence("regime", regime.regime_confidence, weight=1.0),
            PerModuleConfidence("risk_inverse", 1.0 - risk.systemic_risk_score, weight=1.0),
        ]
        if validation.confidence_multiplier == 0.0:
            contributors.append(PerModuleConfidence("validation_zero", 1e-9, weight=2.0))

        confidence_state: ConfidenceState = self.confidence_aggregator.aggregate(
            contributors,
            instability_score=pathology.instability_score,
            contradiction_score=contradiction.contradiction_score,
            entropy_score=pathology.scores.entropy_instability,
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
        )

        envelope = self._build_envelope(
            state=state,
            pathology=pathology,
            regime=regime,
            decision=decision,
            risk=risk,
            contradiction=contradiction,
            confidence_state=confidence_state,
            timeframe_context=timeframe_context,
            validation_failed=validation.validation_failed,
        )
        self._last_envelope = envelope
        return envelope

    def _empty_contradiction(self, state: MarketState, pathology: PathologyReport) -> ContradictionReport:
        return ContradictionReport(
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
            confidence=state.data_quality,
            findings=(),
            contradiction_score=0.0,
            invalid_count=0,
            unstable_count=0,
            critical_count=0,
            validation_failed=False,
            defensive_override=False,
        )

    def _default_decision(self, pathology: PathologyReport, regime: RegimeState) -> DecisionPayload:
        defensive = regime.regime.value in {"DEFENSIVE", "ENTROPIC", "LIQUIDITY_VACUUM"}
        env_label = StrategyEnvironment.DEFENSIVE if defensive else StrategyEnvironment.UNSTABLE
        return DecisionPayload(
            timestamp=pathology.timestamp,
            timeframe=pathology.timeframe,
            source=pathology.source,
            confidence=pathology.structural_health,
            action="OBSERVE_STRUCTURE",
            risk_mode="DEFAULT",
            strategy_bias="NEUTRAL",
            avoid_conditions=("phase0_baseline",),
            structural_bias="NEUTRAL",
            defensive_state=defensive,
            structural_environment=env_label,
            recommended_behavior="observe_structural_evolution",
            execution_safety=max(0.0, 1.0 - pathology.instability_score),
            participation_bias=0.0,
            avoidance_bias=pathology.instability_score,
        )

    def _default_risk(self, pathology: PathologyReport, regime: RegimeState) -> RiskState:
        aggregate = pathology.scores.aggregate
        risk_band = (
            RiskBand.CRITICAL
            if aggregate >= 0.85
            else RiskBand.HIGH
            if aggregate >= 0.7
            else RiskBand.ELEVATED
            if aggregate >= 0.45
            else RiskBand.HEALTHY
        )
        return RiskState(
            timestamp=pathology.timestamp,
            timeframe=pathology.timeframe,
            source=pathology.source,
            confidence=1.0 - aggregate,
            risk_band=risk_band,
            systemic_risk_score=aggregate,
            collapse_probability=min(1.0, 0.5 * aggregate + 0.5 * pathology.escalation_risk),
            instability_probability=pathology.instability_score,
            defensive_risk_modifier=max(0.0, aggregate - 0.5),
            confidence_decay=min(1.0, aggregate),
            participation_safety=max(0.0, 1.0 - aggregate),
            fragility_index=max(
                pathology.scores.liquidity_imbalance,
                pathology.scores.dispersion_shock,
                pathology.scores.volatility_disorder,
            ),
            reasoning=(
                f"baseline_risk_band={risk_band.value}",
                f"aggregate={aggregate:.2f}",
                f"escalation={pathology.escalation_risk:.2f}",
                f"regime={regime.regime.value}",
            ),
        )

    def _build_contradiction_context(
        self,
        *,
        pathology: PathologyReport,
        regime: RegimeState,
        decision: DecisionPayload,
        timeframe_context: TimeframeContext | None,
        pre_aggregation_confidence: float,
    ) -> ContradictionContext:
        s = pathology.scores
        trend_persistence_health = max(0.0, 1.0 - max(s.autocorrelation_breakdown, s.continuation_decay))
        structural_fragmentation = max(s.volatility_disorder, s.dispersion_shock, s.liquidity_imbalance)
        expansion_sustainability = max(0.0, 1.0 - max(s.liquidity_imbalance, s.dispersion_shock))
        structural_balance = max(0.0, 1.0 - pathology.instability_score)
        continuation_state_strength = trend_persistence_health

        regime_is_defensive = 1.0 if regime.regime.value in {"DEFENSIVE", "ENTROPIC", "LIQUIDITY_VACUUM"} else 0.0
        aggressive_participation = decision.participation_bias
        defensive_posture = 1.0 if decision.defensive_state else 0.0

        if timeframe_context is not None:
            macro_instability = max(
                snap.instability_score
                for snap in timeframe_context.snapshots
                if snap.timeframe.order >= 2
            ) if any(s.timeframe.order >= 2 for s in timeframe_context.snapshots) else 0.0
            local_expansion_health = max(
                snap.structural_health
                for snap in timeframe_context.snapshots
                if snap.timeframe.order <= 1
            ) if any(s.timeframe.order <= 1 for s in timeframe_context.snapshots) else 0.0
            timeframe_collapse_risk = timeframe_context.timeframe_conflict_score
            local_optimism = max(
                snap.structural_health
                for snap in timeframe_context.snapshots
                if snap.timeframe.order <= 1
            ) if any(s.timeframe.order <= 1 for s in timeframe_context.snapshots) else 0.0
        else:
            macro_instability = 0.0
            local_expansion_health = 0.0
            timeframe_collapse_risk = 0.0
            local_optimism = 0.0

        return ContradictionContext(
            pathology_aggregate=s.aggregate,
            structural_health=pathology.structural_health,
            instability_score=pathology.instability_score,
            escalation_risk=pathology.escalation_risk,
            entropy_instability=s.entropy_instability,
            autocorrelation_breakdown=s.autocorrelation_breakdown,
            liquidity_imbalance=s.liquidity_imbalance,
            dispersion_shock=s.dispersion_shock,
            volatility_disorder=s.volatility_disorder,
            continuation_decay=s.continuation_decay,
            continuation_confidence=max(0.0, 1.0 - s.continuation_decay),
            trend_persistence_health=trend_persistence_health,
            structural_fragmentation=structural_fragmentation,
            expansion_sustainability=expansion_sustainability,
            structural_balance=structural_balance,
            continuation_state_strength=continuation_state_strength,
            defensive_posture=defensive_posture,
            aggressive_participation=aggressive_participation,
            regime_is_defensive=regime_is_defensive,
            macro_instability=macro_instability,
            local_expansion_health=local_expansion_health,
            timeframe_collapse_risk=timeframe_collapse_risk,
            local_optimism=local_optimism,
            contradiction_score_prior=s.aggregate,
            pre_aggregation_confidence=pre_aggregation_confidence,
        )

    def _market_state_hash(self, state: MarketState) -> str:
        bar = state.current_bar
        material = f"{bar.symbol}|{bar.timestamp.isoformat()}|{bar.timeframe.value}|{bar.open:.10f}|{bar.high:.10f}|{bar.low:.10f}|{bar.close:.10f}|{bar.volume:.10f}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]

    def _build_envelope(
        self,
        *,
        state: MarketState,
        pathology: PathologyReport,
        regime: RegimeState,
        decision: DecisionPayload,
        risk: RiskState,
        contradiction: ContradictionReport,
        confidence_state: ConfidenceState,
        timeframe_context: TimeframeContext | None,
        validation_failed: bool,
    ) -> DiagnosisEnvelope:
        structural_health = pathology.structural_health
        defensive_state = decision.defensive_state or contradiction.defensive_override
        escalation_risk = max(pathology.escalation_risk, risk.systemic_risk_score)

        invalid_pairs = tuple(
            f.pair_id for f in contradiction.findings if f.policy.value == "INVALID"
        )
        suppressors: list[str] = []
        if contradiction.unstable_count:
            suppressors.append(f"unstable:{contradiction.unstable_count}")
        if contradiction.critical_count:
            suppressors.append(f"critical:{contradiction.critical_count}")
        if state.is_stale:
            suppressors.append("stale_data")

        drivers = pathology.reasoning + (
            f"regime={regime.regime.value}",
            f"risk_band={risk.risk_band.value}",
            f"global_conf={confidence_state.global_confidence:.2f}",
        )

        reasoning = DiagnosisReasoning(
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
            confidence=confidence_state.global_confidence,
            summary=(
                f"{regime.regime.value} / {pathology.structural_state.value} | "
                f"health={structural_health:.2f} esc={escalation_risk:.2f} "
                f"conf={confidence_state.global_confidence:.2f}"
            ),
            drivers=drivers,
            invalid_pairs=invalid_pairs,
            suppressors=tuple(suppressors),
        )

        return DiagnosisEnvelope(
            timestamp=state.timestamp,
            timeframe=state.timeframe,
            source=state.source,
            confidence=confidence_state.global_confidence,
            symbol=state.symbol,
            market_state_hash=self._market_state_hash(state),
            structural_health=structural_health,
            escalation_risk=escalation_risk,
            defensive_state=defensive_state,
            pathology=pathology,
            contradiction=contradiction,
            regime=regime,
            risk=risk,
            confidence_state=confidence_state,
            timeframe_context=timeframe_context,
            decision=decision,
            reasoning=reasoning,
            validation_failed=validation_failed,
        )
