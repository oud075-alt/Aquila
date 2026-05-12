"""Walk-forward backtest harness.

A single anomaly is evaluated against a null baseline (typically
``RandomBarSampler``) over a stream of bars. Only the L1 primitive
layer is run; higher layers are deliberately excluded so the detector
is tested in isolation.

Statistical machinery is minimal and explicit:

- ``precision_detector`` / ``precision_baseline`` = success rate over
  bars on which the respective detector fired.
- ``lift`` = ``precision_detector - precision_baseline``.
- ``bootstrap_p_value`` and ``bootstrap_ci_95`` come from a paired
  bootstrap of the success-rate difference (B = 1000).

There is **no** PnL, slippage, or transaction-cost model. This harness
answers only one question: does the detector's success rate beat the
baseline by a statistically significant margin?
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.base import LayerContext
from aquila.core.types import Symbol
from aquila.detectors.schemas import AnomalyDefinition, TriggerRecord
from aquila.governance.export import CognitionExporter  # noqa: F401 (sibling export reuse)
from aquila.outcomes import OutcomeEnricher
from aquila.outcomes.interfaces import TriggerRecord as OutcomeTrigger
from aquila.outcomes.schemas import ForwardOutcome
from aquila.primitives.schemas import PrimitiveBar, PrimitiveSnapshot
from aquila.primitives.service import PrimitiveMetricsLayer


TriggerFn = Callable[[PrimitiveSnapshot, LayerContext], bool]


@dataclass(frozen=True)
class _BarWithTrigger:
    bar: PrimitiveBar
    snap_range_pct: float


class BacktestReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    anomaly_id: str
    version: str
    n_events: int
    n_triggers_detector: int
    n_triggers_baseline: int
    precision_detector: float
    precision_baseline: float
    lift: float
    bootstrap_p_value: float
    bootstrap_ci_95: tuple[float, float]
    success_metric_passed: bool
    schema_version: str = "1.0.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _eval_success(expression: str, outcome: ForwardOutcome) -> bool:
    """Evaluate ``OutcomeRule.success_expression`` in a restricted namespace.

    Only the public fields of ``ForwardOutcome`` plus ``abs`` and ``min``
    / ``max`` are exposed. This is not a sandbox; it is a deliberate
    constraint on what an anomaly definition is allowed to ask.
    """
    namespace = {
        "abs": abs,
        "min": min,
        "max": max,
        "trigger_event_id": outcome.trigger_event_id,
        "horizon_bars": outcome.horizon_bars,
        "realized_return": outcome.realized_return,
        "realized_vol": outcome.realized_vol,
        "max_adverse_excursion": outcome.max_adverse_excursion,
        "max_favorable_excursion": outcome.max_favorable_excursion,
        "range_at_trigger": outcome.range_at_trigger,
    }
    return bool(eval(expression, {"__builtins__": {}}, namespace))


def _bootstrap_diff(
    successes_a: list[int],
    successes_b: list[int],
    *,
    b: int = 1000,
    seed: int = 1337,
) -> tuple[float, tuple[float, float]]:
    """Two-sample bootstrap of the *difference of means*.

    Returns ``(p_value, (ci_lo, ci_hi))`` where ``p_value`` is the
    two-sided probability that the resampled difference has the
    opposite sign of the observed difference, and the CI is empirical
    2.5/97.5 percentiles.

    Edge cases:
    - Empty sample → 0/0 precision is treated as 0.
    - Equal samples → p = 1.0, CI collapses to a point.
    """
    if not successes_a and not successes_b:
        return 1.0, (0.0, 0.0)

    rng = random.Random(seed)

    def _mean(xs: list[int]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    observed = _mean(successes_a) - _mean(successes_b)
    diffs: list[float] = []
    n_a = len(successes_a)
    n_b = len(successes_b)
    for _ in range(b):
        sa = [successes_a[rng.randrange(n_a)] for _ in range(n_a)] if n_a else []
        sb = [successes_b[rng.randrange(n_b)] for _ in range(n_b)] if n_b else []
        diffs.append(_mean(sa) - _mean(sb))
    diffs.sort()

    if observed > 0:
        p = sum(1 for d in diffs if d <= 0) / len(diffs)
    elif observed < 0:
        p = sum(1 for d in diffs if d >= 0) / len(diffs)
    else:
        p = 1.0

    lo = diffs[int(0.025 * (len(diffs) - 1))]
    hi = diffs[int(0.975 * (len(diffs) - 1))]
    return p, (lo, hi)


class WalkForwardBacktest:
    """Run a single detector + baseline over a bar stream.

    ``train_window`` and ``test_window`` are exposed to satisfy the
    walk-forward shape; in v0.1 the harness uses ``train_window`` only
    to skip warm-up bars from precision computation. Multi-fold
    walk-forward is deferred until M2 lands so calibration can be
    rebuilt per fold without lookahead.
    """

    def __init__(
        self,
        definition: AnomalyDefinition,
        trigger_fn: TriggerFn,
        baseline,
        *,
        outcome_enricher: OutcomeEnricher | None = None,
        train_window: int = 100,
        test_window: int | None = None,
        seed: int = 1337,
    ) -> None:
        self._definition = definition
        self._trigger_fn = trigger_fn
        self._baseline = baseline
        self._enricher = outcome_enricher or OutcomeEnricher()
        self._train_window = max(0, train_window)
        self._test_window = test_window
        self._seed = seed

    def run(self, bars: Iterable[PrimitiveBar], *, symbol: Symbol) -> BacktestReport:
        bars_list = list(bars)
        ctx = LayerContext(correlation_id=str(uuid.uuid4()), symbol=symbol)

        prim = PrimitiveMetricsLayer(window=self._train_window or 50)

        detector_triggers: list[OutcomeTrigger] = []
        baseline_triggers: list[OutcomeTrigger] = []

        for idx, bar in enumerate(bars_list):
            snap_out = prim.process(bar, ctx)
            snap: PrimitiveSnapshot = snap_out.payload  # type: ignore[assignment]

            in_train = idx < self._train_window
            in_test = (
                True
                if self._test_window is None
                else (idx < self._train_window + self._test_window)
            )

            if not in_test:
                break

            fired_det = self._trigger_fn(snap, ctx)
            fired_base = self._baseline.fire(snap, ctx)

            if in_train:
                continue

            # Trigger fires AT the close of bar i. We timestamp it one
            # microsecond AFTER the bar so the lookahead guard in
            # ``OutcomeEnricher`` rejects the trigger bar itself as a
            # candidate for the forward window. Bars from i+1 onward
            # satisfy ``bar.timestamp > trigger.timestamp``.
            event_ts = bar.timestamp + timedelta(microseconds=1)
            if fired_det:
                detector_triggers.append(OutcomeTrigger(
                    trigger_event_id=f"D-{idx}-{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    timestamp=event_ts,
                    range_at_trigger=snap.range_pct,
                    anomaly_id=self._definition.anomaly_id,
                    anomaly_version=self._definition.version,
                ))
            if fired_base:
                baseline_triggers.append(OutcomeTrigger(
                    trigger_event_id=f"B-{idx}-{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    timestamp=event_ts,
                    range_at_trigger=snap.range_pct,
                    anomaly_id=f"{self._definition.anomaly_id}.baseline",
                    anomaly_version=self._definition.version,
                ))

        horizon = self._definition.outcome_rule.horizon_bars
        det_outcomes = self._enricher.enrich(detector_triggers, bars_list, horizon_bars=horizon)
        base_outcomes = self._enricher.enrich(baseline_triggers, bars_list, horizon_bars=horizon)

        det_successes = [
            int(_eval_success(self._definition.outcome_rule.success_expression, o))
            for o in det_outcomes.values()
        ]
        base_successes = [
            int(_eval_success(self._definition.outcome_rule.success_expression, o))
            for o in base_outcomes.values()
        ]

        prec_det = sum(det_successes) / len(det_successes) if det_successes else 0.0
        prec_base = sum(base_successes) / len(base_successes) if base_successes else 0.0
        lift = prec_det - prec_base
        p_value, ci = _bootstrap_diff(det_successes, base_successes, seed=self._seed)

        threshold = self._definition.success_metric.threshold
        passed = (
            prec_det >= threshold
            and lift > 0
            and p_value < 0.05
            and len(det_successes) > 0
        )

        return BacktestReport(
            anomaly_id=self._definition.anomaly_id,
            version=self._definition.version,
            n_events=len(bars_list),
            n_triggers_detector=len(detector_triggers),
            n_triggers_baseline=len(baseline_triggers),
            precision_detector=prec_det,
            precision_baseline=prec_base,
            lift=lift,
            bootstrap_p_value=p_value,
            bootstrap_ci_95=ci,
            success_metric_passed=passed,
        )


def _import_builtin_detector(anomaly_id: str):
    """Resolve a builtin detector by id. Returns (DEFINITION, trigger)."""
    canonical_id = anomaly_id.lower().replace("-", "_")
    module = importlib.import_module(f"aquila.detectors.builtin.{canonical_id}")
    return module.DEFINITION, module.trigger


def _load_bars(path: Path) -> list[PrimitiveBar]:
    """Tiny loader. Supports .jsonl for now. Parquet support deferred."""
    bars: list[PrimitiveBar] = []
    if path.suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    bars.append(PrimitiveBar.model_validate_json(line))
    else:
        raise NotImplementedError(
            f"Bar loader does not yet support {path.suffix}. "
            f"Use .jsonl. Parquet support is intentionally deferred until "
            f"M4 widens the data path."
        )
    return bars


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walk-forward backtest CLI")
    parser.add_argument("--detector", required=True, help="Anomaly id, e.g. MSPIS-A-001")
    parser.add_argument("--data", required=True, help="Path to bars file (.jsonl)")
    parser.add_argument("--symbol", default="X")
    parser.add_argument("--train-window", type=int, default=200)
    parser.add_argument("--test-window", type=int, default=None)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--out", default=None, help="Optional output JSON path")
    parser.add_argument("--out-jsonld", default=None, help="Optional JSON-LD output path")
    args = parser.parse_args(argv)

    definition, trigger_fn = _import_builtin_detector(args.detector)

    from aquila.detectors.baselines import RandomBarSampler

    bars = _load_bars(Path(args.data))
    target_rate = 0.05
    backtest = WalkForwardBacktest(
        definition=definition,
        trigger_fn=trigger_fn,
        baseline=RandomBarSampler(seed=args.seed, target_rate=target_rate),
        train_window=args.train_window,
        test_window=args.test_window,
        seed=args.seed,
    )
    report = backtest.run(bars, symbol=Symbol(args.symbol))
    blob = report.model_dump(mode="json")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(blob, indent=2, default=str) + "\n")
    if args.out_jsonld:
        Path(args.out_jsonld).parent.mkdir(parents=True, exist_ok=True)
        ld = {
            "@context": {
                "@vocab": "https://aquila.local/ontology#",
                "BacktestReport": "BacktestReport",
            },
            "@type": "BacktestReport",
            **blob,
        }
        Path(args.out_jsonld).write_text(json.dumps(ld, indent=2, default=str) + "\n")
    print(json.dumps(blob, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
