"""Schemas for forward outcomes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from aquila.core.types import Symbol


class ForwardOutcome(BaseModel):
    """Realised forward outcome for a single trigger event.

    All fields are computed from bars strictly *after* the trigger
    timestamp. The enricher enforces this guard.
    """

    model_config = ConfigDict(frozen=True)

    trigger_event_id: str
    symbol: Symbol
    horizon_bars: int
    realized_return: float
    realized_vol: float
    max_adverse_excursion: float
    max_favorable_excursion: float
    range_at_trigger: float
    closed_at: datetime
    schema_version: str = "1.0.0"
