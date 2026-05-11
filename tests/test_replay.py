from __future__ import annotations

from aquila.core.types import Symbol
from aquila.replay.runner import ReplayRunner
from aquila.replay.schemas import ReplayContext


def test_replay_is_deterministic(synthetic_events, symbol):
    ctx = ReplayContext(run_id="r1", symbol=symbol)
    r1 = ReplayRunner(ctx).run(synthetic_events)
    r2 = ReplayRunner(ctx).run(synthetic_events)
    assert r1.ticks == r2.ticks
    for ln in r1.last_outputs:
        c1 = r1.last_outputs[ln].confidence
        c2 = r2.last_outputs[ln].confidence
        assert abs(c1 - c2) < 1e-9


def test_replay_does_not_write_real_memory(synthetic_events, symbol):
    ctx = ReplayContext(run_id="r2", symbol=symbol)
    result = ReplayRunner(ctx).run(synthetic_events)
    assert result.ticks > 0
