"""Replay slicing — closes audit gap #59."""

from __future__ import annotations

from typing import Iterable, Iterator

from aquila.ingestion.schemas import RawEvent
from aquila.replay.schemas import ReplaySlice


class ReplaySlicer:
    def slice(self, events: Iterable[RawEvent], window: ReplaySlice) -> Iterator[RawEvent]:
        for e in events:
            if window.start <= e.timestamp <= window.end:
                yield e
