"""End-to-end pipeline integration tests."""

from __future__ import annotations

import asyncio

import pytest

from brain.orchestrator import Orchestrator
from brain.schemas import DiagnosisLabel, SeverityLevel, StandardizedDiagnosis


@pytest.mark.asyncio
async def test_full_pipeline_runs_end_to_end():
    orchestrator = Orchestrator()
    try:
        diag = await orchestrator.diagnose_symbol(
            symbol="BTC/USDT",
            timeframe="1m",
            exchange="binance",
            include_gpt=False,
        )
    finally:
        await orchestrator.shutdown()

    assert isinstance(diag, StandardizedDiagnosis)
    assert diag.symbol == "BTC/USDT"
    assert diag.timeframe == "1m"
    assert isinstance(diag.market_state, DiagnosisLabel)
    assert isinstance(diag.severity, SeverityLevel)
    assert 0.0 <= diag.overall_pathology() <= 1.0
    assert 0.0 <= diag.confidence_scores.overall_confidence <= 1.0
    assert len(diag.causal_reasoning) > 0
    # standardized diagnosis must contain all sub-objects
    assert diag.expectation is not None
    assert diag.actual is not None
    assert diag.volatility_state is not None
    assert diag.liquidity_state is not None
    assert diag.continuation_state is not None
    assert diag.instability_state is not None
    assert diag.escalation_risk is not None
    assert diag.structural_health is not None
    assert diag.transition_state is not None
    assert "projection" in diag.extra
    assert isinstance(diag.diagnostic_summary, str) and diag.diagnostic_summary


@pytest.mark.asyncio
async def test_pipeline_handles_multiple_symbols():
    orchestrator = Orchestrator()
    try:
        diagnoses = []
        for symbol in ("BTC/USDT", "ETH/USDT"):
            d = await orchestrator.diagnose_symbol(symbol=symbol, timeframe="5m", include_gpt=False)
            diagnoses.append(d)
    finally:
        await orchestrator.shutdown()

    labels = {d.symbol: d.market_state.value for d in diagnoses}
    assert "BTC/USDT" in labels and "ETH/USDT" in labels
    for d in diagnoses:
        assert 0.0 <= d.overall_pathology() <= 1.0
