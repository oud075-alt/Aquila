"""Pathology primitives and engine sanity checks."""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from core.ingestion import OHLCVPipeline, ReplayAdapter
from core.pathology import PathologyEngine
from core.pathology.metrics import (
    directional_efficiency,
    lag1_autocorr,
    robust_zscore,
    wilder_atr,
)
from core.schemas.enums import SourceMode, Timeframe


def test_wilder_atr_positive() -> None:
    h = np.array([10, 11, 12, 13, 14, 13, 12], dtype=float)
    lo = np.array([9, 10, 11, 12, 11, 10, 11], dtype=float)
    c = np.array([9.5, 10.5, 11.5, 12.5, 12.0, 11.0, 11.5], dtype=float)
    assert wilder_atr(h, lo, c, period=3) > 0


def test_directional_efficiency_bounded() -> None:
    closes = np.linspace(100, 110, 32)
    assert 0.0 <= directional_efficiency(closes) <= 1.0
    noisy = np.tile([100.0, 101.0], 16)
    de = directional_efficiency(noisy)
    assert 0.0 <= de < 0.2


def test_lag1_autocorr_within_range() -> None:
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    assert -1.0 <= lag1_autocorr(arr) <= 1.0


def test_robust_zscore_handles_empty_history() -> None:
    assert robust_zscore(1.0, np.array([])) == 0.0


def test_pathology_scores_bounded(tmp_path: Path) -> None:
    parquet = Path(__file__).with_name("fixtures") / "btcusdt_1m_sample.parquet"
    if not parquet.exists():
        from tests.fixtures.generate_btcusdt_sample import write_default

        write_default(parquet)

    async def _run() -> list[float]:
        adapter = ReplayAdapter(parquet, timeframe=Timeframe.ONE_MIN)
        pipe = OHLCVPipeline(timeframe=Timeframe.ONE_MIN, source=SourceMode.REPLAY)
        engine = PathologyEngine()
        aggs: list[float] = []
        async for event in adapter.stream():
            state = pipe.push(event)
            report = engine.compute(state)
            aggs.append(report.scores.aggregate)
            for v in report.scores.vector:
                assert 0.0 <= v <= 1.0, "primitive out of bounds"
            assert 0.0 <= report.structural_health <= 1.0
            assert 0.0 <= report.escalation_risk <= 1.0
            assert 0.0 <= report.instability_score <= 1.0
        return aggs

    aggs = asyncio.run(_run())
    assert len(aggs) > 100
    assert max(aggs) <= 1.0
    assert min(aggs) >= 0.0


def test_pathology_state_classification_diverse() -> None:
    parquet = Path(__file__).with_name("fixtures") / "btcusdt_1m_sample.parquet"

    async def _run() -> set[str]:
        adapter = ReplayAdapter(parquet, timeframe=Timeframe.ONE_MIN)
        pipe = OHLCVPipeline(timeframe=Timeframe.ONE_MIN, source=SourceMode.REPLAY)
        engine = PathologyEngine()
        seen: set[str] = set()
        async for event in adapter.stream():
            state = pipe.push(event)
            seen.add(engine.classifier.classify(state).value)
        return seen

    seen = asyncio.run(_run())
    assert len(seen) >= 4, f"expected at least 4 distinct structural states, got {seen}"
