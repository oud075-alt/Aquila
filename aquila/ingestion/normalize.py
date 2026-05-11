"""Timestamp normalization + idempotent deduplication."""

from __future__ import annotations

from datetime import timezone

from aquila.ingestion.interfaces import IngestionGateway
from aquila.ingestion.schemas import RawEvent


class IngestionNormalizer(IngestionGateway):
    """In-memory gateway. For distributed deployments, swap with a Kafka-/
    NATS-backed implementation that shares the dedup window across nodes.
    """

    def __init__(self, dedup_window: int = 65536) -> None:
        self._seen: dict[str, None] = {}
        self._max = dedup_window

    def ingest(self, event: RawEvent) -> RawEvent | None:
        key = event.idempotency_key or event.event_id
        if key in self._seen:
            return None
        self._seen[key] = None
        if len(self._seen) > self._max:
            for k in list(self._seen.keys())[: self._max // 4]:
                self._seen.pop(k, None)
        ts = event.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
            event = event.model_copy(update={"timestamp": ts})
        return event
