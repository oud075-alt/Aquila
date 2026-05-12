"""Numeric correctness tests for ``OutcomeEnricher``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aquila.core.types import Symbol
from aquila.outcomes import OutcomeEnricher, OutcomeStore
from aquila.outcomes.interfaces import TriggerRecord
from aquila.primitives.schemas import PrimitiveBar


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_bar(i: int, o: float, h: float, l: float, c: float) -> PrimitiveBar:
    return PrimitiveBar(
        timestamp=T0 + timedelta(minutes=i),
        open=o, high=h, low=l, close=c, volume=1.0,
    )


def test_realized_return_matches_entry_to_close():
    trig = TriggerRecord(trigger_event_id="t", symbol=Symbol("X"), timestamp=T0)
    bars = [
        _make_bar(1, 100, 105, 99, 104),
        _make_bar(2, 104, 110, 103, 108),
        _make_bar(3, 108, 112, 106, 110),
    ]
    result = OutcomeEnricher().enrich([trig], bars, horizon_bars=3)
    assert "t" in result
    fo = result["t"]
    assert fo.horizon_bars == 3
    # entry = open of first forward bar = 100; close = close of last bar = 110
    assert abs(fo.realized_return - (110 - 100) / 100) < 1e-9
    assert fo.max_favorable_excursion > 0
    assert fo.max_adverse_excursion <= 0
    assert fo.closed_at == bars[-1].timestamp


def test_horizon_too_short_skips_outcome():
    trig = TriggerRecord(trigger_event_id="t", symbol=Symbol("X"), timestamp=T0)
    bars = [_make_bar(1, 100, 101, 99, 100)]
    result = OutcomeEnricher().enrich([trig], bars, horizon_bars=3)
    assert "t" not in result


def test_outcome_store_roundtrip(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    store = OutcomeStore(path=path)
    trig = TriggerRecord(trigger_event_id="t1", symbol=Symbol("X"), timestamp=T0)
    bars = [
        _make_bar(1, 100, 101, 99, 100),
        _make_bar(2, 100, 102, 99, 101),
    ]
    result = OutcomeEnricher().enrich([trig], bars, horizon_bars=2)
    for fo in result.values():
        store.append(fo)
    assert len(store) == 1

    reloaded = OutcomeStore(path=path)
    assert len(reloaded) == 1
    assert reloaded.get("t1").trigger_event_id == "t1"
