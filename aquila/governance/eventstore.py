"""Append-only event store. Closes 'event sourcing enforcement' requirement."""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName, Symbol, utcnow


class StoredEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    sequence: int
    layer: LayerName
    symbol: Symbol
    event_id: str
    correlation_id: str
    timestamp: datetime
    confidence: float
    visibility: str
    schema_version: str
    payload_type: str
    payload: dict
    stored_at: datetime = Field(default_factory=utcnow)


class EventStore:
    def __init__(self) -> None:
        self._events: list[StoredEvent] = []

    def append(self, output: LayerOutput) -> StoredEvent:
        ev = StoredEvent(
            sequence=len(self._events),
            layer=output.layer,
            symbol=output.symbol,
            event_id=output.event_id,
            correlation_id=output.correlation_id,
            timestamp=output.timestamp,
            confidence=output.confidence,
            visibility=output.visibility,
            schema_version=output.schema_version,
            payload_type=type(output.payload).__name__,
            payload=output.payload.model_dump() if hasattr(output.payload, "model_dump") else {},
        )
        self._events.append(ev)
        return ev

    def stream(self) -> Iterator[StoredEvent]:
        return iter(list(self._events))

    def __len__(self) -> int:
        return len(self._events)
