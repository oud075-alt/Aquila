"""In-process and replay adapters. Production deployments add Kafka/WS."""

from __future__ import annotations

from collections import deque
from typing import Iterable, Iterator

from aquila.ingestion.interfaces import MarketDataAdapter
from aquila.ingestion.schemas import RawEvent


class InProcAdapter(MarketDataAdapter):
    """Push-mode adapter. Callers `enqueue()` events; orchestrator `stream()`s.
    Single-process; not thread-safe. Use only for tests / replay.
    """

    source_id = "inproc"

    def __init__(self) -> None:
        self._q: deque[RawEvent] = deque()

    def enqueue(self, event: RawEvent) -> None:
        self._q.append(event)

    def stream(self) -> Iterator[RawEvent]:
        while self._q:
            yield self._q.popleft()


class ReplayAdapter(MarketDataAdapter):
    """Deterministic ordered replay over a finite iterable of events."""

    source_id = "replay"

    def __init__(self, events: Iterable[RawEvent]) -> None:
        self._events = list(events)

    def stream(self) -> Iterator[RawEvent]:
        for ev in self._events:
            yield ev.model_copy(update={"origin": "replay"})
