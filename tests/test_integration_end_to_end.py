"""End-to-end integration — Phase 0 → 5 wired through the orchestrator."""

from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path

from brain import (
    AdaptiveLearningEngine,
    ContextFusionEngine,
    DecisionEngine,
    RiskIntelligenceEngine,
    StrategyRouter,
)
from core.ingestion import ReplayAdapter
from core.orchestrator import DiagnosisCoordinator
from core.schemas.diagnosis_envelope import DiagnosisEnvelope
from core.schemas.enums import Timeframe


def _build_coordinator() -> tuple[DiagnosisCoordinator, AdaptiveLearningEngine]:
    learning = AdaptiveLearningEngine()
    decision = DecisionEngine()
    risk = RiskIntelligenceEngine()
    fusion = ContextFusionEngine()
    router = StrategyRouter()
    coord = DiagnosisCoordinator(
        decision_hook=decision.decide,
        risk_hook=risk.evaluate,
        context_fusion_hook=fusion.fuse,
        strategy_router_hook=router.route,
        adaptive_learning_hook=learning,
    )
    return coord, learning


def test_full_pipeline_produces_complete_envelopes(sample_parquet: Path) -> None:
    coord, _ = _build_coordinator()
    adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)

    async def _run() -> list[DiagnosisEnvelope]:
        envelopes: list[DiagnosisEnvelope] = []
        async for env in coord.diagnose_stream(adapter):
            envelopes.append(env)
        return envelopes

    envs = asyncio.run(_run())
    assert len(envs) == 512
    for env in envs:
        assert env.pathology is not None
        assert env.regime is not None
        assert env.risk is not None
        assert env.decision is not None
        assert env.confidence_state is not None
        assert env.timeframe_context is not None
        assert env.reasoning.summary
        assert 0.0 <= env.confidence_state.global_confidence <= 1.0
        assert 0.0 <= env.structural_health <= 1.0
        assert 0.0 <= env.escalation_risk <= 1.0


def test_regime_diversity_in_full_run(sample_parquet: Path) -> None:
    coord, _ = _build_coordinator()
    adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)

    async def _run() -> Counter[str]:
        c: Counter[str] = Counter()
        async for env in coord.diagnose_stream(adapter):
            c[env.regime.regime.value] += 1
        return c

    counts = asyncio.run(_run())
    assert len(counts) >= 4, f"expected ≥4 distinct regimes, got {counts}"


def test_decision_actions_obey_anti_drift(sample_parquet: Path) -> None:
    coord, _ = _build_coordinator()
    adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)

    forbidden_action_substrings = (
        "buy",
        "sell",
        "long",
        "short",
        "entry",
        "stop",
        "take_profit",
    )

    async def _run() -> set[str]:
        actions: set[str] = set()
        async for env in coord.diagnose_stream(adapter):
            actions.add(env.decision.action)
            actions.add(env.decision.strategy_bias)
            actions.add(env.decision.structural_bias)
        return actions

    actions = asyncio.run(_run())
    bad = [
        a for a in actions if any(sub in a.lower() for sub in forbidden_action_substrings)
    ]
    assert not bad, f"forbidden action labels detected: {bad}"


def test_invalid_diagnoses_force_zero_confidence(sample_parquet: Path) -> None:
    coord, _ = _build_coordinator()
    adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)

    async def _run() -> None:
        async for env in coord.diagnose_stream(adapter):
            if env.validation_failed:
                assert env.confidence_state.global_confidence < 0.1
                assert env.defensive_state is True
            if env.contradiction.critical_count > 0:
                assert env.defensive_state is True
            if env.confidence_state.global_confidence > 0.5:
                assert not env.validation_failed

    asyncio.run(_run())


def test_adaptive_learning_observes_every_bar(sample_parquet: Path) -> None:
    coord, learning = _build_coordinator()
    adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)

    async def _run() -> int:
        n = 0
        async for _env in coord.diagnose_stream(adapter):
            n += 1
        return n

    n = asyncio.run(_run())
    assert n == 512
    assert len(learning._pending) == 512


def test_high_instability_high_continuation_combo_is_impossible(sample_parquet: Path) -> None:
    """Diagnostic consistency lock — these two cannot coexist (Appendix N #1)."""
    coord, _ = _build_coordinator()
    adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)

    async def _run() -> None:
        async for env in coord.diagnose_stream(adapter):
            cont_conf = 1.0 - env.pathology.scores.continuation_decay
            if env.pathology.instability_score >= 0.70 and cont_conf >= 0.70:
                assert env.contradiction.invalid_count >= 1 or env.validation_failed, (
                    "consistency violation: HIGH instability and HIGH continuation confidence "
                    "both present without contradiction flag"
                )

    asyncio.run(_run())
