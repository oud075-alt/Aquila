"""Interfaces for outcomes module."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from aquila.core.types import Symbol


class TriggerRecord(BaseModel):
    """Minimal trigger envelope consumed by the enricher.

    Real triggers are produced by registered detectors (see
    ``aquila.detectors``); this lightweight model is here so the
    outcomes module does not import from detectors and stays acyclic.
    """

    model_config = ConfigDict(frozen=True)

    trigger_event_id: str
    symbol: Symbol
    timestamp: datetime
    range_at_trigger: float = 0.0
    anomaly_id: str = ""
    anomaly_version: str = ""


class OutcomeStoreProto(Protocol):
    def append(self, outcome) -> None: ...
    def all(self) -> list: ...
    def __len__(self) -> int: ...
