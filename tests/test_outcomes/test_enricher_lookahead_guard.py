"""Lookahead guard tests for ``OutcomeEnricher``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aquila.core.types import Symbol
from aquila.outcomes import LookaheadError, OutcomeEnricher
from aquila.outcomes.interfaces import TriggerRecord
from aquila.primitives.schemas import PrimitiveBar


def _bar(t: datetime, c: float = 100.0) -> PrimitiveBar:
    return PrimitiveBar(timestamp=t, open=c, high=c + 0.5, low=c - 0.5,
                        close=c, volume=1.0)


def test_lookahead_guard_rejects_same_timestamp():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trig = TriggerRecord(trigger_event_id="e1", symbol=Symbol("X"), timestamp=t)
    bars = [_bar(t)]
    with pytest.raises(LookaheadError):
        OutcomeEnricher().enrich([trig], bars, horizon_bars=1)


def test_lookahead_guard_rejects_same_timestamp_even_when_extra_forward_bars_present():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trig = TriggerRecord(trigger_event_id="e1", symbol=Symbol("X"), timestamp=t0)
    bars = [
        _bar(t0),
        _bar(t0 + timedelta(minutes=1)),
        _bar(t0 + timedelta(minutes=2)),
    ]
    with pytest.raises(LookaheadError):
        OutcomeEnricher().enrich([trig], bars, horizon_bars=2)


def test_strictly_past_bars_silently_ignored():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trig = TriggerRecord(trigger_event_id="e1", symbol=Symbol("X"), timestamp=t)
    bars = [
        _bar(t - timedelta(minutes=2)),
        _bar(t - timedelta(minutes=1)),
        _bar(t + timedelta(minutes=1)),
        _bar(t + timedelta(minutes=2)),
    ]
    result = OutcomeEnricher().enrich([trig], bars, horizon_bars=2)
    assert "e1" in result
    assert result["e1"].horizon_bars == 2


def test_horizon_must_be_positive():
    with pytest.raises(ValueError):
        OutcomeEnricher().enrich([], [], horizon_bars=0)
