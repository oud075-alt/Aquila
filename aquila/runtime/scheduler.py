from __future__ import annotations

from typing import Iterable

from aquila.ingestion.schemas import RawEvent


class ReplayScheduler:
    """Deterministic ordered scheduler for a replay run. Production
    deployments distribute slices across workers; in-proc default runs
    sequentially for replay-equivalence guarantees.
    """

    def schedule(self, events: Iterable[RawEvent]) -> list[RawEvent]:
        return sorted(events, key=lambda e: e.timestamp)
