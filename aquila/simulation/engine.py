"""Simulation engine — counterfactual replay + synthetic-event injection.

All synthetic events are tagged `origin="synthetic"`. The L4 memory engine
refuses to persist synthetic episodes (write_on_real=True path); this
prevents memory contamination.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from aquila.ingestion.schemas import OHLCV, RawEvent, RawEventKind
from aquila.replay.runner import ReplayRunner
from aquila.replay.schemas import ReplayContext
from aquila.simulation.schemas import (
    CounterfactualResult,
    ScenarioStressResult,
)
from aquila.core.types import Symbol


class SimulationEngine:
    def counterfactual(
        self, events: Iterable[RawEvent], *, label: str = "cf", run_id: str = "cf-1"
    ) -> CounterfactualResult:
        ctx = ReplayContext(run_id=run_id, symbol=next(iter(events)).symbol if events else Symbol("UNKNOWN"))
        runner = ReplayRunner(ctx)
        result = runner.run(events)
        return CounterfactualResult(label=label, ticks=result.ticks, summary={"run_id": result.run_id})

    def stress(
        self,
        symbol: Symbol,
        n_cycles: int = 50,
        volatility_multiplier: float = 3.0,
    ) -> ScenarioStressResult:
        events: list[RawEvent] = []
        base = 100.0
        for i in range(n_cycles):
            ts = datetime(2026, 1, 1, tzinfo=timezone.utc).replace(minute=i % 60)
            move = volatility_multiplier * (0.5 if i % 2 == 0 else -0.5)
            events.append(RawEvent(
                kind=RawEventKind.OHLCV, symbol=symbol,
                timestamp=ts, received_at=ts, origin="synthetic",
                ohlcv=OHLCV(timeframe="M1", open=base, high=base + abs(move),
                            low=base - abs(move), close=base + move, volume=10),
            ))
            base += move
        ctx = ReplayContext(run_id="stress", symbol=symbol, origin="synthetic")
        result = ReplayRunner(ctx).run(events)
        max_unc = 0.0
        max_inst = 0.0
        from aquila.core.types import LayerName
        meta = result.last_outputs.get(LayerName.META)
        reg = result.last_outputs.get(LayerName.REGIME)
        if meta:
            max_unc = float(meta.payload.uncertainty.total)
        if reg:
            max_inst = float(reg.payload.instability_score)
        return ScenarioStressResult(
            scenario_name="vol_stress", cycles_run=result.ticks,
            max_uncertainty=max_unc, max_instability=max_inst,
        )
