"""Behavioral tests for ``FalsificationTestRunner``.

These tests do NOT assert on the truth of any scientific claim; they
assert that the runner correctly reports pass/fail when the underlying
pytest node id is missing, empty, or present-and-passing.
"""

from __future__ import annotations

import warnings

import pytest

from aquila.governance.assumptions import Assumption, AssumptionRegistry
from aquila.validation.falsifiability import (
    FalsifiabilityChecker,
    FalsificationTestRunner,
)


def _registry_with(node_id: str) -> AssumptionRegistry:
    reg = AssumptionRegistry()
    reg._a.clear()
    reg.register(Assumption(
        namespace="t", name="case",
        statement="test stub",
        falsifiable_by=node_id,
        risk_if_violated="",
    ))
    return reg


def test_empty_falsifiable_by_is_false():
    reg = _registry_with("")
    runner = FalsificationTestRunner(reg)
    assert runner.check() == {"t.case": False}
    assert runner.all_falsifiable() is False


def test_missing_node_id_is_false():
    reg = _registry_with(
        "tests/falsification/test_does_not_exist.py::test_nope"
    )
    runner = FalsificationTestRunner(reg)
    assert runner.check() == {"t.case": False}


def test_real_node_id_passes_through():
    reg = _registry_with(
        "tests/falsification/test_bounded_reflexivity.py::test_meta_depth_above_one_raises"
    )
    runner = FalsificationTestRunner(reg)
    result = runner.check()
    assert result == {"t.case": True}
    assert runner.all_falsifiable() is True


def test_seeded_registry_is_falsifiable():
    runner = FalsificationTestRunner(AssumptionRegistry())
    result = runner.check()
    assert set(result.keys()) == {
        "structural.bar_closed_data",
        "deception.no_signal_emission",
        "memory.origin_isolation",
        "meta.bounded_reflexivity",
    }
    assert all(result.values()) is True


def test_clearing_falsifiable_by_breaks_validation():
    reg = AssumptionRegistry()
    reg._a[0] = reg._a[0].model_copy(update={"falsifiable_by": ""})
    runner = FalsificationTestRunner(reg)
    assert runner.all_falsifiable() is False


def test_deprecated_alias_emits_warning():
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        FalsifiabilityChecker(_registry_with(""))
    assert any(issubclass(w.category, DeprecationWarning) for w in records)
