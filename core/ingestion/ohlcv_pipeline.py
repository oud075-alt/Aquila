"""OHLCV pipeline — converts a stream of bars into rolling MarketState windows.

Maintains a bounded ring buffer of recent bars, emits a `MarketState` per
incoming bar, and surfaces stale-data + partial-bar metadata into the state's
`data_quality`, `is_stale`, `watermark_lag_seconds` fields.
"""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator
from datetime import datetime

from core.ingestion.base_adapter import IngestionEvent
from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL, MarketBar, MarketState

DEFAULT_TAIL_LENGTH: int = 256


class OHLCVPipeline:
    """Build rolling MarketStates from an async ingestion stream."""

    def __init__(
        self,
        *,
        timeframe: Timeframe,
        source: SourceMode,
        symbol: str = DEFAULT_SYMBOL,
        tail_length: int = DEFAULT_TAIL_LENGTH,
        stale_after_bars: float = 2.0,
    ) -> None:
        if tail_length < 1:
            raise ValueError("tail_length must be >= 1")
        if stale_after_bars <= 0:
            raise ValueError("stale_after_bars must be positive")
        self.timeframe = timeframe
        self.source = source
        self.symbol = symbol.upper()
        self.tail_length = tail_length
        self.stale_after_bars = stale_after_bars
        self._buffer: deque[MarketBar] = deque(maxlen=tail_length + 1)
        self._last_event_time: datetime | None = None

    def _compute_quality(self, event: IngestionEvent) -> tuple[float, bool, float]:
        lag_seconds = max(event.lag_seconds, 0.0)
        bars_lag = lag_seconds / self.timeframe.seconds
        is_stale = bars_lag > self.stale_after_bars or event.is_recovered

        quality = 1.0
        if event.is_partial:
            quality *= 0.5
        if event.is_recovered:
            quality *= 0.25
        if bars_lag > 0:
            quality *= max(0.05, 1.0 - 0.25 * bars_lag)
        quality = max(0.0, min(1.0, quality))
        return quality, is_stale, lag_seconds

    def push(self, event: IngestionEvent) -> MarketState:
        """Push one ingestion event and synthesize a MarketState."""
        if event.bar.timeframe != self.timeframe:
            raise ValueError(
                f"OHLCVPipeline timeframe={self.timeframe} got bar tf={event.bar.timeframe}"
            )
        if self._last_event_time is not None and event.event_time <= self._last_event_time:
            return self._snapshot(event)
        self._buffer.append(event.bar)
        self._last_event_time = event.event_time
        return self._snapshot(event)

    def _snapshot(self, event: IngestionEvent) -> MarketState:
        if not self._buffer:
            raise RuntimeError("OHLCVPipeline snapshot called before any bar buffered")
        bars = tuple(self._buffer)
        current = bars[-1]
        tail = bars[:-1]
        quality, is_stale, lag_seconds = self._compute_quality(event)
        return MarketState(
            timestamp=current.timestamp,
            timeframe=self.timeframe,
            source=self.source,
            confidence=quality,
            symbol=self.symbol,
            current_bar=current,
            tail=tail,
            data_quality=quality,
            is_stale=is_stale,
            watermark_lag_seconds=lag_seconds,
        )

    async def stream(self, events: AsyncIterator[IngestionEvent]) -> AsyncIterator[MarketState]:
        async for event in events:
            yield self.push(event)
