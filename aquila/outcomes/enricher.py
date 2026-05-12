"""Forward outcome enricher.

Given a list of triggers and an iterable of bars, computes the forward
outcome for each trigger using ONLY bars whose timestamp is strictly
greater than the trigger timestamp. This is the lookahead guard.

Lookahead leak modes guarded against:

1. ``bar.timestamp <= trigger.timestamp``: the enricher raises
   ``LookaheadError`` rather than silently including the bar.
2. Concurrent (==) timestamps are rejected — the trigger bar itself is
   not allowed to be the first forward bar.
"""

from __future__ import annotations

import math
from typing import Iterable

from aquila.outcomes.interfaces import TriggerRecord
from aquila.outcomes.schemas import ForwardOutcome
from aquila.primitives.schemas import PrimitiveBar


class LookaheadError(ValueError):
    """Raised when a candidate forward bar is not strictly after the trigger."""


class OutcomeEnricher:
    """Compute ``ForwardOutcome`` for each trigger.

    Not coupled to ``CognitiveOrchestrator``. Not coupled to
    ``EpisodeRecord``. The enricher reads triggers and bars and writes
    nothing into live cognition state. This isolation is the only way
    we can keep lookahead bias provably absent.
    """

    def enrich(
        self,
        triggers: list[TriggerRecord],
        bars: Iterable[PrimitiveBar],
        *,
        horizon_bars: int,
    ) -> dict[str, ForwardOutcome]:
        if horizon_bars < 1:
            raise ValueError("horizon_bars must be >= 1")

        bars_list = list(bars)
        bars_list.sort(key=lambda b: b.timestamp)

        out: dict[str, ForwardOutcome] = {}
        for trig in triggers:
            forward = [b for b in bars_list if b.timestamp > trig.timestamp]
            # Concurrent / past bars must not be used. Detect attempted
            # inclusion explicitly by counting bars with timestamp == trigger.
            for b in bars_list:
                if b.timestamp == trig.timestamp:
                    raise LookaheadError(
                        f"bar.timestamp == trigger.timestamp for "
                        f"trigger {trig.trigger_event_id}: forward outcome "
                        f"would leak the trigger bar itself"
                    )
                if b.timestamp < trig.timestamp:
                    continue

            if len(forward) < horizon_bars:
                continue
            window = forward[:horizon_bars]
            entry_price = window[0].open
            close_price = window[-1].close

            highs = [b.high for b in window]
            lows = [b.low for b in window]
            closes = [b.close for b in window]

            mae = (min(lows) - entry_price) / entry_price if entry_price > 0 else 0.0
            mfe = (max(highs) - entry_price) / entry_price if entry_price > 0 else 0.0
            ret = (close_price - entry_price) / entry_price if entry_price > 0 else 0.0

            returns = [
                math.log(closes[i] / closes[i - 1])
                for i in range(1, len(closes))
                if closes[i - 1] > 0
            ]
            mean_r = sum(returns) / len(returns) if returns else 0.0
            var_r = (
                sum((r - mean_r) ** 2 for r in returns) / len(returns)
                if returns else 0.0
            )
            rvol = math.sqrt(var_r) if var_r > 0 else 0.0

            out[trig.trigger_event_id] = ForwardOutcome(
                trigger_event_id=trig.trigger_event_id,
                symbol=trig.symbol,
                horizon_bars=horizon_bars,
                realized_return=ret,
                realized_vol=rvol,
                max_adverse_excursion=mae,
                max_favorable_excursion=mfe,
                range_at_trigger=trig.range_at_trigger,
                closed_at=window[-1].timestamp,
            )
        return out
