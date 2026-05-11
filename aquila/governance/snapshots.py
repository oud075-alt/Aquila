"""Cognitive snapshot/checkpoint format. Closes audit gap #65."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import utcnow
from aquila.governance.eventstore import StoredEvent


class CognitiveSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    captured_at: datetime = Field(default_factory=utcnow)
    schema_version: str = "1.0.0"
    last_sequence: int
    events: list[StoredEvent] = Field(default_factory=list)


class SnapshotManager:
    def __init__(self) -> None:
        self._snapshots: list[CognitiveSnapshot] = []

    def capture(self, events: list[StoredEvent]) -> CognitiveSnapshot:
        last_seq = events[-1].sequence if events else -1
        snap = CognitiveSnapshot(last_sequence=last_seq, events=list(events))
        self._snapshots.append(snap)
        return snap

    def latest(self) -> CognitiveSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None
