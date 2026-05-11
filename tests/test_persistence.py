"""Persistence round-trip and migration tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from core.ingestion import ReplayAdapter
from core.orchestrator import DiagnosisCoordinator
from core.persistence import (
    CURRENT_PERSISTENCE_VERSION,
    MemoryStore,
    SQLiteDiagnosisStore,
    TimeSeriesStore,
)
from core.schemas.enums import Timeframe


def test_persistence_version_is_current(tmp_path: Path) -> None:
    store = SQLiteDiagnosisStore(tmp_path / "x.db")
    assert store.persistence_version == CURRENT_PERSISTENCE_VERSION


def test_diagnosis_roundtrip(tmp_path: Path, sample_parquet: Path) -> None:
    db = SQLiteDiagnosisStore(tmp_path / "diag.db")
    ts = TimeSeriesStore(tmp_path / "ts")

    async def _run() -> int:
        adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)
        coord = DiagnosisCoordinator()
        n = 0
        async for env in coord.diagnose_stream(adapter):
            db.write_diagnosis(env)
            ts.append(env)
            n += 1
        ts.flush()
        return n

    n = asyncio.run(_run())
    assert n == db.count() == 512

    df = ts.read_all()
    assert len(df) == 512
    assert df["pathology_aggregate"].between(0.0, 1.0).all()

    latest = db.latest(symbol="BTCUSDT", timeframe="1m")
    assert latest is not None
    assert latest.regime is not None
    db.close()


def test_memory_store_round_trip(tmp_path: Path) -> None:
    mem = MemoryStore(tmp_path / "mem.db")
    mid = mem.remember(
        symbol="BTCUSDT",
        timeframe=Timeframe.ONE_MIN,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        kind="test",
        payload={"x": 1, "y": [1, 2, 3]},
        outcome_score=None,
    )
    assert mid > 0
    assert mem.count() == 1
    entries = mem.recall()
    assert entries[0].payload["x"] == 1
    mem.assign_outcome(mid, outcome_score=0.42)
    after = mem.recall()
    assert after[0].outcome_score == 0.42
    mem.close()
