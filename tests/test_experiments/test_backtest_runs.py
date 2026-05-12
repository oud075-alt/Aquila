"""Structural / report-shape tests for the walk-forward backtest harness.

Per HARD RULE #6 these tests do NOT assert that the detector passes or
fails its precision threshold. They assert that the report is a valid
``BacktestReport`` with all the expected fields and that the bootstrap
mechanics work on tiny synthetic inputs.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aquila.core.types import Symbol
from aquila.detectors.baselines import RandomBarSampler
from aquila.detectors.builtin.mspis_a_001 import DEFINITION, reset_state, trigger
from aquila.experiments.backtest import (
    BacktestReport,
    WalkForwardBacktest,
    _bootstrap_diff,
    _eval_success,
    main,
)
from aquila.outcomes.schemas import ForwardOutcome
from aquila.primitives.schemas import PrimitiveBar


def _random_walk_bars(n: int = 400, seed: int = 42) -> list[PrimitiveBar]:
    rng = random.Random(seed)
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = 100.0
    for i in range(n):
        move = rng.uniform(-0.4, 0.4)
        high = price + abs(move) + rng.uniform(0.05, 0.5)
        low = price - abs(move) - rng.uniform(0.05, 0.5)
        close = price + move
        vol = max(0.1, 10.0 + rng.uniform(-3.0, 5.0))
        bars.append(PrimitiveBar(
            timestamp=t0 + timedelta(minutes=i),
            open=price, high=high, low=low, close=close, volume=vol,
        ))
        price = close
    return bars


def test_report_has_all_required_fields():
    reset_state()
    bt = WalkForwardBacktest(
        definition=DEFINITION,
        trigger_fn=trigger,
        baseline=RandomBarSampler(seed=42, target_rate=0.05),
        train_window=80,
    )
    report = bt.run(_random_walk_bars(), symbol=Symbol("X"))
    assert isinstance(report, BacktestReport)
    assert report.anomaly_id == "MSPIS-A-001"
    assert report.version == "0.1.0"
    assert report.n_events > 0
    assert report.schema_version
    assert isinstance(report.bootstrap_ci_95, tuple)
    assert len(report.bootstrap_ci_95) == 2
    assert 0.0 <= report.precision_detector <= 1.0
    assert 0.0 <= report.precision_baseline <= 1.0
    assert isinstance(report.success_metric_passed, bool)


def test_report_serialises_to_json():
    reset_state()
    bt = WalkForwardBacktest(
        definition=DEFINITION,
        trigger_fn=trigger,
        baseline=RandomBarSampler(seed=42, target_rate=0.05),
        train_window=80,
    )
    report = bt.run(_random_walk_bars(), symbol=Symbol("X"))
    blob = report.model_dump_json()
    parsed = json.loads(blob)
    assert parsed["anomaly_id"] == "MSPIS-A-001"
    assert "bootstrap_p_value" in parsed
    assert "schema_version" in parsed


def test_bootstrap_handles_equal_samples():
    p, ci = _bootstrap_diff([1, 0, 1, 0], [1, 0, 1, 0])
    assert 0.0 <= p <= 1.0
    assert ci[0] <= ci[1]


def test_bootstrap_handles_empty_samples():
    p, ci = _bootstrap_diff([], [])
    assert p == 1.0
    assert ci == (0.0, 0.0)


def test_success_expression_evaluation():
    out = ForwardOutcome(
        trigger_event_id="t",
        symbol=Symbol("X"),
        horizon_bars=10,
        realized_return=0.001,
        realized_vol=0.0,
        max_adverse_excursion=0.0,
        max_favorable_excursion=0.0,
        range_at_trigger=0.02,
        closed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert _eval_success("abs(realized_return) <= 0.5 * range_at_trigger", out) is True
    assert _eval_success("realized_return > 1.0", out) is False


def test_cli_writes_report(tmp_path):
    reset_state()
    bars = _random_walk_bars(200)
    bars_path = tmp_path / "bars.jsonl"
    with bars_path.open("w", encoding="utf-8") as f:
        for b in bars:
            f.write(b.model_dump_json() + "\n")
    out_path = tmp_path / "report.json"
    rc = main([
        "--detector", "MSPIS-A-001",
        "--data", str(bars_path),
        "--symbol", "X",
        "--train-window", "80",
        "--out", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["anomaly_id"] == "MSPIS-A-001"
    assert "bootstrap_p_value" in data
