from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from aquila.core.base import LayerContext
from aquila.core.types import Symbol
from aquila.ingestion.schemas import OHLCV, RawEvent, RawEventKind
from aquila.pipeline import CognitiveOrchestrator
from aquila.primitives import PrimitiveBar


@pytest.fixture
def symbol() -> Symbol:
    return Symbol("BTCUSDT")


@pytest.fixture
def ctx(symbol: Symbol) -> LayerContext:
    return LayerContext(correlation_id="test-corr", symbol=symbol)


@pytest.fixture
def synthetic_bars():
    random.seed(7)
    bars = []
    base = 100.0
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(80):
        move = random.uniform(-0.5, 0.5)
        h = base + abs(move) + random.uniform(0.1, 0.4)
        l = base - abs(move) - random.uniform(0.1, 0.4)
        c = base + move
        v = 10 + random.uniform(-3, 5)
        bars.append(PrimitiveBar(
            timestamp=t0 + timedelta(minutes=i),
            open=base, high=h, low=l, close=c, volume=max(0.1, v),
        ))
        base = c
    return bars


@pytest.fixture
def synthetic_events(symbol: Symbol, synthetic_bars):
    out = []
    for b in synthetic_bars:
        out.append(RawEvent(
            kind=RawEventKind.OHLCV, symbol=symbol,
            timestamp=b.timestamp, received_at=b.timestamp,
            ohlcv=OHLCV(timeframe="M1", open=b.open, high=b.high,
                        low=b.low, close=b.close, volume=b.volume),
        ))
    return out


@pytest.fixture
def orchestrator() -> CognitiveOrchestrator:
    return CognitiveOrchestrator()
