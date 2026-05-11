"""Stress / fault-tolerance tests."""

from __future__ import annotations

import asyncio
import time

import pytest

from brain.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_pipeline_under_concurrent_load():
    orchestrator = Orchestrator()
    try:
        coros = [
            orchestrator.diagnose_symbol(symbol="BTC/USDT", timeframe="1m", include_gpt=False)
            for _ in range(8)
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)
    finally:
        await orchestrator.shutdown()

    assert len(results) == 8
    for r in results:
        assert not isinstance(r, Exception), f"diagnose raised: {r}"


@pytest.mark.asyncio
async def test_pipeline_runs_with_unsupported_exchange():
    orchestrator = Orchestrator()
    try:
        diag = await orchestrator.diagnose_symbol(
            symbol="XAUUSD", timeframe="1m", exchange="mt5", include_gpt=False
        )
    finally:
        await orchestrator.shutdown()
    assert diag.symbol == "XAUUSD"
    assert diag.timeframe == "1m"


@pytest.mark.asyncio
async def test_pipeline_throughput():
    orchestrator = Orchestrator()
    try:
        start = time.time()
        for _ in range(3):
            await orchestrator.diagnose_symbol(symbol="BTC/USDT", timeframe="5m", include_gpt=False)
        elapsed = time.time() - start
    finally:
        await orchestrator.shutdown()
    # The synthetic fallback must complete < 60s for 3 diagnoses on CI-class HW
    assert elapsed < 60.0
