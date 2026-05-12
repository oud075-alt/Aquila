"""MSPIS-A-001 — expansion_without_volume_mean_reversion (v0.1.0).

Detector definition migrated from the legacy
``aquila/pathology/service.py`` rule. The success metric here is a
*claim* about what we expect to be true on out-of-sample data; M1.5
runs the actual backtest and records whether the claim holds.

Trigger heuristic (v0.1.0):

- range_pct of the current bar is in the top decile of the rolling
  200-bar window;
- volume_z <= -0.3 (volume is below average given the same window).

The rolling threshold is computed in-detector for v0.1.0. M2.2 will
replace this with a ``CalibrationStore`` lookup so the threshold is
calibrated per-symbol / per-timeframe without lookahead.
"""

from __future__ import annotations

from collections import deque

from aquila.core.base import LayerContext
from aquila.core.types import LayerName
from aquila.detectors.schemas import (
    AnomalyDefinition,
    AnomalyScope,
    OutcomeRule,
    SuccessMetric,
)
from aquila.primitives.schemas import PrimitiveSnapshot

WINDOW_BARS: int = 200
TOP_DECILE: float = 0.9
VOLUME_Z_MAX: float = -0.3
MIN_WARMUP: int = 50


DEFINITION: AnomalyDefinition = AnomalyDefinition(
    anomaly_id="MSPIS-A-001",
    version="0.1.0",
    name="expansion_without_volume_mean_reversion",
    description=(
        "A bar in the top decile of recent range that fires on below-average "
        "volume frequently mean-reverts within 10 bars. Hypothesis only — "
        "no empirical validation yet. The M1.5 backtest decides whether the "
        "success_metric below holds on OOS data."
    ),
    scope=AnomalyScope(symbols=["*"], timeframes=["M5", "M15", "H1"]),
    inputs_required=[LayerName.PRIMITIVES],
    trigger_rule_ref="aquila.detectors.builtin.mspis_a_001:trigger",
    outcome_rule=OutcomeRule(
        horizon_bars=10,
        success_expression="abs(realized_return) <= 0.5 * range_at_trigger",
    ),
    success_metric=SuccessMetric(
        metric="precision",
        threshold=0.55,
        baseline="random_bar_sampler",
        significance="bootstrap_p<0.05",
    ),
)


class _RollingState:
    """Per-(symbol, timeframe) rolling buffer of range_pct values.

    Kept module-level (keyed) for v0.1.0; the rolling threshold is
    derived from values *strictly before* the current bar so there is
    no lookahead in the trigger itself.
    """

    def __init__(self) -> None:
        self.range_pcts: dict[tuple[str, str], deque[float]] = {}

    def update(self, key: tuple[str, str], range_pct: float) -> None:
        dq = self.range_pcts.setdefault(key, deque(maxlen=WINDOW_BARS))
        dq.append(range_pct)

    def quantile_before_update(
        self, key: tuple[str, str], q: float
    ) -> float | None:
        """Return the q-quantile of the history *before* the latest append.

        Returns ``None`` when warm-up is insufficient.
        """
        dq = self.range_pcts.get(key)
        if dq is None:
            return None
        sample = list(dq)[:-1] if len(dq) > 0 else []
        if len(sample) < MIN_WARMUP:
            return None
        sample.sort()
        idx = max(0, min(len(sample) - 1, int(q * (len(sample) - 1))))
        return sample[idx]


_STATE = _RollingState()


def reset_state() -> None:
    """Clear the rolling buffers. Used by tests and the backtest harness."""
    _STATE.range_pcts.clear()


def trigger(snap: PrimitiveSnapshot, ctx: LayerContext) -> bool:
    """Return True iff the bar satisfies the MSPIS-A-001 trigger rule.

    Timeframe is read from ``ctx.meta_signal['timeframe']`` if present
    (the orchestrator sets it via the ingestion layer); otherwise the
    default "M5" key is used. This means evaluation across multiple
    timeframes requires separate ``ctx.meta_signal`` payloads.

    The function intentionally does not catch exceptions — HARD RULE #7.
    Any malformed input should surface immediately.
    """
    timeframe = str(ctx.meta_signal.get("timeframe", "M5"))
    key = (str(ctx.symbol), timeframe)
    _STATE.update(key, snap.range_pct)

    threshold = _STATE.quantile_before_update(key, TOP_DECILE)
    if threshold is None:
        return False
    if snap.range_pct < threshold:
        return False
    if snap.volume_z > VOLUME_Z_MAX:
        return False
    return True
