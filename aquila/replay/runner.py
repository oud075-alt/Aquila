"""Deterministic replay runner.

Uses `ReplayClock` (frozen time, advances via event timestamps) and a
memory layer configured with `write_on_real=False` to prevent contamination.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.base import LayerOutput
from aquila.core.clock import ReplayClock
from aquila.core.types import LayerName
from aquila.ingestion.schemas import RawEvent
from aquila.memory.replay_integration import make_replay_memory
from aquila.pipeline import CognitiveOrchestrator
from aquila.primitives import PrimitiveBar
from aquila.replay.schemas import ReplayContext


class ReplayResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    run_id: str
    ticks: int
    last_outputs: dict[LayerName, LayerOutput] = Field(default_factory=dict)


class ReplayRunner:
    def __init__(self, replay_ctx: ReplayContext) -> None:
        self._ctx = replay_ctx

    def run(self, events: Iterable[RawEvent]) -> ReplayResult:
        events = list(events)
        if not events:
            return ReplayResult(run_id=self._ctx.run_id, ticks=0)

        clock = ReplayClock(events[0].timestamp)
        orch = CognitiveOrchestrator(clock=clock, memory=make_replay_memory())

        last: dict[LayerName, LayerOutput] = {}
        count = 0
        for ev in events:
            if ev.kind.value != "ohlcv" or ev.ohlcv is None:
                continue
            clock.advance(ev.timestamp)
            bar = PrimitiveBar(
                timestamp=ev.timestamp,
                open=ev.ohlcv.open, high=ev.ohlcv.high,
                low=ev.ohlcv.low, close=ev.ohlcv.close,
                volume=ev.ohlcv.volume,
            )
            last = orch.run_tick(ev.symbol, bar, origin=self._ctx.origin)
            count += 1
        return ReplayResult(run_id=self._ctx.run_id, ticks=count, last_outputs=last)
