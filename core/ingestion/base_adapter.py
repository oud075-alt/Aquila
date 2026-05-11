"""Base adapter interface for all ingestion sources.

Adapters are async iterators emitting `IngestionEvent` objects. Each event
carries a fully-validated `MarketBar` plus event-time and processing-time
metadata for watermark management.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import MarketBar


@dataclass(frozen=True, slots=True)
class IngestionEvent:
    """Single ingestion emission with event-time / processing-time stamps."""

    bar: MarketBar
    processing_time: datetime
    event_time: datetime
    sequence: int
    is_recovered: bool = False
    is_partial: bool = False
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def lag_seconds(self) -> float:
        return (self.processing_time - self.event_time).total_seconds()


class BaseAdapter(abc.ABC):
    """Abstract async-iterator adapter.

    Subclasses implement `_stream()` which yields `IngestionEvent`s in
    event-time order (or with bounded out-of-order tolerance handled
    by the OHLCV pipeline downstream).
    """

    def __init__(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        source: SourceMode,
        watermark_tolerance_bars: int = 2,
    ) -> None:
        if watermark_tolerance_bars < 0:
            raise ValueError("watermark_tolerance_bars must be >= 0")
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        self.source = source
        self.watermark_tolerance_bars = watermark_tolerance_bars
        self._sequence: int = 0

    @abc.abstractmethod
    async def _stream(self) -> AsyncIterator[IngestionEvent]:
        """Subclass stream implementation. Must yield in event-time order."""
        raise NotImplementedError
        if False:  # pragma: no cover - typing aid for AsyncIterator inference
            yield

    async def stream(self) -> AsyncIterator[IngestionEvent]:
        """Public entry point — wraps `_stream()` and stamps sequence numbers."""
        async for event in self._stream():
            self._sequence += 1
            yield IngestionEvent(
                bar=event.bar,
                processing_time=event.processing_time,
                event_time=event.event_time,
                sequence=self._sequence,
                is_recovered=event.is_recovered,
                is_partial=event.is_partial,
                meta=event.meta,
            )

    def now_utc(self) -> datetime:
        """Wall-clock UTC. Overridden in tests for determinism."""
        return datetime.now(tz=UTC)
