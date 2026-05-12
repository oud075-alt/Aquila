"""Schema contract tests — every Phase 0A schema must enforce its invariants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from core.schemas import (
    DiagnosisEnvelope,
    MarketBar,
    MarketState,
    SourceMode,
    Timeframe,
)


def _ts() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _bar(**kw: object) -> MarketBar:
    defaults = {
        "timestamp": _ts(),
        "timeframe": Timeframe.ONE_MIN,
        "source": SourceMode.REPLAY,
        "confidence": 1.0,
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 105.0,
        "volume": 1000.0,
    }
    defaults.update(kw)
    return MarketBar(**defaults)  # type: ignore[arg-type]


def test_marketbar_requires_utc_timestamp() -> None:
    with pytest.raises(ValidationError):
        _bar(timestamp=datetime(2026, 1, 1))


def test_marketbar_low_open_high_relationship() -> None:
    with pytest.raises(ValidationError):
        _bar(open=150.0)


def test_marketbar_immutable() -> None:
    bar = _bar()
    with pytest.raises(ValidationError):
        bar.open = 999.0  # type: ignore[misc]


def test_marketbar_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        MarketBar(
            timestamp=_ts(),
            timeframe=Timeframe.ONE_MIN,
            source=SourceMode.REPLAY,
            confidence=1.0,
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
            mystery_field="x",  # type: ignore[call-arg]
        )


def test_marketstate_tail_must_be_monotonic() -> None:
    b1 = _bar()
    b2 = _bar(timestamp=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))
    with pytest.raises(ValidationError):
        MarketState(
            timestamp=b1.timestamp,
            timeframe=Timeframe.ONE_MIN,
            source=SourceMode.REPLAY,
            confidence=1.0,
            current_bar=b1,
            tail=(b2,),
        )


def test_marketstate_window_includes_current() -> None:
    b_tail = _bar(timestamp=datetime(2025, 12, 31, 23, 59, tzinfo=UTC))
    b_current = _bar()
    ms = MarketState(
        timestamp=b_current.timestamp,
        timeframe=Timeframe.ONE_MIN,
        source=SourceMode.REPLAY,
        confidence=1.0,
        current_bar=b_current,
        tail=(b_tail,),
    )
    assert len(ms) == 2
    assert ms.window[-1] is b_current


def test_diagnosis_envelope_has_all_mandatory_fields() -> None:
    fields = set(DiagnosisEnvelope.model_fields.keys())
    required = {
        "schema_version",
        "timestamp",
        "timeframe",
        "source",
        "confidence",
        "pathology",
        "contradiction",
        "regime",
        "risk",
        "confidence_state",
        "decision",
        "reasoning",
        "structural_health",
        "escalation_risk",
        "defensive_state",
        "timeframe_context",
    }
    missing = required - fields
    assert not missing, f"DiagnosisEnvelope missing fields: {missing}"
