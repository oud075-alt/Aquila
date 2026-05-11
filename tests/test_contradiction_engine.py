"""Contradiction matrix + validator behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.contradiction import (
    ConfidenceAggregator,
    ConsistencyValidator,
    ContradictionContext,
    ContradictionMatrix,
    PerModuleConfidence,
)
from core.schemas.enums import ContradictionPolicy, SourceMode, Timeframe


def _ctx(**overrides: float) -> ContradictionContext:
    base = dict(
        pathology_aggregate=0.5,
        structural_health=0.5,
        instability_score=0.5,
        escalation_risk=0.5,
        entropy_instability=0.5,
        autocorrelation_breakdown=0.5,
        liquidity_imbalance=0.5,
        dispersion_shock=0.5,
        volatility_disorder=0.5,
        continuation_decay=0.5,
        continuation_confidence=0.5,
        trend_persistence_health=0.5,
        structural_fragmentation=0.5,
        expansion_sustainability=0.5,
        structural_balance=0.5,
        continuation_state_strength=0.5,
        defensive_posture=0.5,
        aggressive_participation=0.5,
        regime_is_defensive=0.0,
        macro_instability=0.0,
        local_expansion_health=0.0,
        timeframe_collapse_risk=0.0,
        local_optimism=0.0,
        contradiction_score_prior=0.0,
        pre_aggregation_confidence=0.5,
    )
    base.update(overrides)
    return ContradictionContext(**base)


def test_matrix_loads_twelve_rules() -> None:
    m = ContradictionMatrix()
    assert len(m.rules) == 12
    assert m.high_threshold == pytest.approx(0.70)
    assert m.low_threshold == pytest.approx(0.30)


def test_invalid_high_pathology_vs_high_health_fires() -> None:
    m = ContradictionMatrix()
    findings = m.evaluate(_ctx(pathology_aggregate=0.9, structural_health=0.9))
    fired = {r.id for r, _ in findings}
    assert "INVALID_HIGH_PATHOLOGY_VS_HIGH_HEALTH" in fired


def test_invalid_high_instability_vs_continuation_fires() -> None:
    m = ContradictionMatrix()
    findings = m.evaluate(_ctx(instability_score=0.9, continuation_confidence=0.9))
    assert any(r.policy == ContradictionPolicy.INVALID for r, _ in findings)


def test_critical_defensive_regime_vs_aggressive_participation() -> None:
    m = ContradictionMatrix()
    findings = m.evaluate(_ctx(regime_is_defensive=1.0, aggressive_participation=0.9))
    assert any(
        r.id == "CRITICAL_DEFENSIVE_REGIME_VS_AGGRESSIVE_PARTICIPATION" for r, _ in findings
    )


def test_validator_invalid_forces_zero_confidence() -> None:
    v = ConsistencyValidator()
    result = v.validate(
        context=_ctx(pathology_aggregate=0.95, structural_health=0.95),
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        timeframe=Timeframe.ONE_MIN,
        source=SourceMode.REPLAY,
        base_confidence=0.9,
    )
    assert result.validation_failed
    assert result.confidence_multiplier == 0.0
    assert result.defensive_override
    assert result.report.invalid_count >= 1


def test_validator_clean_state_produces_no_findings() -> None:
    v = ConsistencyValidator()
    result = v.validate(
        context=_ctx(
            pathology_aggregate=0.2,
            structural_health=0.8,
            instability_score=0.2,
            continuation_confidence=0.5,
            structural_fragmentation=0.2,
            entropy_instability=0.5,
            escalation_risk=0.2,
            defensive_posture=0.5,
            regime_is_defensive=0.0,
            aggressive_participation=0.2,
            trend_persistence_health=0.5,
            volatility_disorder=0.2,
            structural_balance=0.5,
            liquidity_imbalance=0.2,
            expansion_sustainability=0.5,
            continuation_decay=0.2,
            continuation_state_strength=0.5,
        ),
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        timeframe=Timeframe.ONE_MIN,
        source=SourceMode.REPLAY,
        base_confidence=0.9,
    )
    assert not result.validation_failed
    assert result.confidence_multiplier == 1.0


def test_confidence_aggregator_penalties_decrease_confidence() -> None:
    agg = ConfidenceAggregator()
    high_noise = agg.aggregate(
        [PerModuleConfidence("a", 0.9)],
        instability_score=0.9,
        contradiction_score=0.9,
        entropy_score=0.9,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        timeframe=Timeframe.ONE_MIN,
        source=SourceMode.REPLAY,
    )
    low_noise = agg.aggregate(
        [PerModuleConfidence("a", 0.9)],
        instability_score=0.0,
        contradiction_score=0.0,
        entropy_score=0.0,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        timeframe=Timeframe.ONE_MIN,
        source=SourceMode.REPLAY,
    )
    assert high_noise.global_confidence < low_noise.global_confidence
