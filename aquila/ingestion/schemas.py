"""Ingestion schemas — immutable, idempotent, lineage-tagged."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Symbol
from aquila.core.base import Origin


class RawEventKind(str, Enum):
    TICK = "tick"
    OHLCV = "ohlcv"
    ORDERFLOW = "orderflow"
    MACRO = "macro"
    SYNTHETIC = "synthetic"


class OHLCV(BaseModel):
    model_config = ConfigDict(frozen=True)
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class OrderFlowEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    side: Literal["bid", "ask"]
    price: float
    size: float
    aggressive: bool = False


class MacroEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    indicator: str
    value: float
    surprise: float | None = None


class RawEvent(BaseModel):
    """Canonical ingested event.

    - `idempotency_key` lets the gateway dedupe replayed feeds.
    - `origin` discriminates real / synthetic / replay events so the memory
      store can prevent synthetic contamination.
    - `source_id` + `trust_score` propagate to the deception layer.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0.0"
    kind: RawEventKind
    symbol: Symbol
    timestamp: datetime
    received_at: datetime
    source_id: str = "default"
    trust_score: float = 1.0
    origin: Origin = "real"
    idempotency_key: str | None = None
    ohlcv: OHLCV | None = None
    orderflow: OrderFlowEvent | None = None
    macro: MacroEvent | None = None
    raw_payload: dict = Field(default_factory=dict)
