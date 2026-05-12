"""Behavioural tests for ``DetectorRegistry`` and ``AnomalyDefinition``."""

from __future__ import annotations

import pytest

from aquila.detectors import (
    AnomalyDefinition,
    AnomalyScope,
    DetectorRegistry,
    OutcomeRule,
    SuccessMetric,
)


def _definition(anomaly_id: str = "TEST-001", version: str = "0.1.0") -> AnomalyDefinition:
    return AnomalyDefinition(
        anomaly_id=anomaly_id,
        version=version,
        name="test_anomaly",
        scope=AnomalyScope(),
        outcome_rule=OutcomeRule(horizon_bars=5, success_expression="realized_return > 0"),
        success_metric=SuccessMetric(),
    )


def test_register_and_lookup():
    reg = DetectorRegistry()
    reg.register(_definition(), lambda snap, ctx: False)
    assert len(reg) == 1
    d, fn = reg.get("TEST-001", "0.1.0")
    assert d.name == "test_anomaly"
    assert callable(fn)


def test_duplicate_registration_raises():
    reg = DetectorRegistry()
    reg.register(_definition(), lambda snap, ctx: False)
    with pytest.raises(ValueError):
        reg.register(_definition(), lambda snap, ctx: False)


def test_multiple_versions_allowed():
    reg = DetectorRegistry()
    reg.register(_definition(version="0.1.0"), lambda snap, ctx: False)
    reg.register(_definition(version="0.2.0"), lambda snap, ctx: True)
    assert len(reg) == 2


def test_missing_lookup_raises():
    reg = DetectorRegistry()
    with pytest.raises(KeyError):
        reg.get("MISSING", "0.0.0")
