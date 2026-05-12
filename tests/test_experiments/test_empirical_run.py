"""Determinism contract for the committed MSPIS-A-001 v0.1.0 empirical run.

This test does NOT assert that the detector passes its success metric
(HARD RULE #6). It asserts that:

- the committed fixture exists and has 2000 bars;
- regenerating the fixture from seed 42 reproduces the committed file
  byte-for-byte;
- re-running the backtest with the documented seed reproduces the
  committed report's headline numbers.

If any of these break, the ADR-0007 record is no longer reproducible
and must be re-run.
"""

from __future__ import annotations

import json
from pathlib import Path

from aquila.core.types import Symbol
from aquila.detectors.baselines import RandomBarSampler
from aquila.detectors.builtin.mspis_a_001 import DEFINITION, reset_state, trigger
from aquila.experiments.backtest import WalkForwardBacktest
from aquila.primitives.schemas import PrimitiveBar
from tests.data.generate_synthetic_seed42 import _generate

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "data" / "synthetic_bars_seed42.jsonl"
REPORT = ROOT / "docs" / "empirical" / "MSPIS-A-001-v0.1.0.json"


def _load_fixture() -> list[PrimitiveBar]:
    bars = []
    with FIXTURE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                bars.append(PrimitiveBar.model_validate_json(line))
    return bars


def test_fixture_exists_and_is_2000_bars():
    assert FIXTURE.exists(), "committed synthetic fixture missing"
    bars = _load_fixture()
    assert len(bars) == 2000


def test_fixture_is_reproducible_from_seed_42():
    regenerated = _generate(n=2000, seed=42)
    committed = _load_fixture()
    assert len(regenerated) == len(committed)
    for a, b in zip(regenerated, committed):
        assert a == b


def test_empirical_report_is_recomputable():
    assert REPORT.exists(), "committed empirical report missing"
    committed = json.loads(REPORT.read_text())

    reset_state()
    bars = _load_fixture()
    backtest = WalkForwardBacktest(
        definition=DEFINITION,
        trigger_fn=trigger,
        baseline=RandomBarSampler(seed=1337, target_rate=0.05),
        train_window=250,
        seed=1337,
    )
    report = backtest.run(bars, symbol=Symbol("SYN42"))

    assert report.n_events == committed["n_events"]
    assert report.n_triggers_detector == committed["n_triggers_detector"]
    assert report.n_triggers_baseline == committed["n_triggers_baseline"]
    assert abs(report.precision_detector - committed["precision_detector"]) < 1e-9
    assert abs(report.precision_baseline - committed["precision_baseline"]) < 1e-9
    assert abs(report.lift - committed["lift"]) < 1e-9
    assert report.success_metric_passed is committed["success_metric_passed"]
