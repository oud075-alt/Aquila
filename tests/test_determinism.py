"""Appendix S — Deterministic replay reproducibility.

Identical Parquet input MUST produce byte-identical diagnosis outputs.

This test runs the full pipeline twice against the same fixture and asserts
that the canonical JSON serialization of every envelope is identical.

Determinism enforcement (per Appendix S):
    - PYTHONHASHSEED, OMP/MKL/NUMEXPR_NUM_THREADS pinned by ReplayAdapter
    - numpy + python random seeded to 0
    - no wall-clock processing time leaks into computation
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from core.ingestion import ReplayAdapter
from core.orchestrator import DiagnosisCoordinator
from core.schemas.enums import Timeframe


def _canonical_dump(envelope_dict: dict[str, object]) -> str:
    return json.dumps(envelope_dict, sort_keys=True, separators=(",", ":"), default=str)


async def _run_once(parquet: Path) -> list[str]:
    adapter = ReplayAdapter(parquet, timeframe=Timeframe.ONE_MIN, seed=0)
    coord = DiagnosisCoordinator()
    out: list[str] = []
    async for env in coord.diagnose_stream(adapter):
        out.append(_canonical_dump(env.model_dump(mode="json")))
    return out


def test_replay_is_byte_identical(sample_parquet: Path) -> None:
    first = asyncio.run(_run_once(sample_parquet))
    second = asyncio.run(_run_once(sample_parquet))
    assert len(first) == len(second), "diagnosis count mismatch"
    differences: list[int] = []
    for i, (a, b) in enumerate(zip(first, second, strict=True)):
        if a != b:
            differences.append(i)
    assert not differences, (
        f"determinism violation at indices {differences[:5]} (showing first 5; "
        f"total {len(differences)})"
    )


def test_replay_full_hash_stable(sample_parquet: Path) -> None:
    first = asyncio.run(_run_once(sample_parquet))
    h1 = hashlib.sha256("\n".join(first).encode()).hexdigest()
    second = asyncio.run(_run_once(sample_parquet))
    h2 = hashlib.sha256("\n".join(second).encode()).hexdigest()
    assert h1 == h2, f"full-run hash drifted: {h1} != {h2}"


def test_replay_envelope_count_matches_input(sample_parquet: Path) -> None:
    envs = asyncio.run(_run_once(sample_parquet))
    assert len(envs) == 512, f"expected 512 diagnoses, got {len(envs)}"
