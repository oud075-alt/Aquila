"""Tick → OHLCV aggregator for live ingestion.

Tick events arrive irregularly. The TickPipeline groups them into fixed-width
timeframe buckets and emits a `MarketBar` when a bucket closes. A provisional
bar is emitted as `is_partial=True` while the current bucket is still open.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL, MarketBar


@dataclass(frozen=True, slots=True)
class Tick:
    """Single trade tick."""

    timestamp: datetime
    price: float
    volume: float
    symbol: str = DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError(f"tick price must be positive, got {self.price}")
        if self.volume < 0:
            raise ValueError(f"tick volume must be non-negative, got {self.volume}")
        if self.timestamp.tzinfo is None:
            raise ValueError("tick timestamp must be timezone-aware UTC")


class TickPipeline:
    """Aggregates ticks into bars of a given timeframe."""

    def __init__(
        self,
        *,
        timeframe: Timeframe,
        source: SourceMode = SourceMode.LIVE_WS,
        symbol: str = DEFAULT_SYMBOL,
    ) -> None:
        self.timeframe = timeframe
        self.source = source
        self.symbol = symbol.upper()
        self._bucket_start: datetime | None = None
        self._open: float | None = None
        self._high: float = 0.0
        self._low: float = 0.0
        self._close: float = 0.0
        self._volume: float = 0.0

    def _bucket_of(self, ts: datetime) -> datetime:
        tf = self.timeframe.seconds
        epoch = int(ts.timestamp())
        bucket = (epoch // tf) * tf
        return datetime.fromtimestamp(bucket, tz=UTC)

    def _emit(self, *, is_partial: bool) -> MarketBar | None:
        if self._bucket_start is None or self._open is None:
            return None
        return MarketBar(
            timestamp=self._bucket_start,
            timeframe=self.timeframe,
            source=self.source,
            confidence=0.5 if is_partial else 1.0,
            symbol=self.symbol,
            open=self._open,
            high=self._high,
            low=self._low,
            close=self._close,
            volume=self._volume,
            is_partial=is_partial,
        )

    def feed(self, tick: Tick) -> tuple[MarketBar | None, MarketBar | None]:
        """Push a tick. Returns (closed_bar_or_None, provisional_bar_or_None)."""
        bucket = self._bucket_of(tick.timestamp)
        closed: MarketBar | None = None

        if self._bucket_start is None:
            self._bucket_start = bucket
            self._open = tick.price
            self._high = tick.price
            self._low = tick.price
            self._close = tick.price
            self._volume = tick.volume
        elif bucket != self._bucket_start:
            closed = self._emit(is_partial=False)
            self._bucket_start = bucket
            self._open = tick.price
            self._high = tick.price
            self._low = tick.price
            self._close = tick.price
            self._volume = tick.volume
        else:
            self._high = max(self._high, tick.price)
            self._low = min(self._low, tick.price)
            self._close = tick.price
            self._volume += tick.volume

        provisional = self._emit(is_partial=True)
        return closed, provisional

    async def aggregate(self, ticks: AsyncIterator[Tick]) -> AsyncIterator[MarketBar]:
        async for t in ticks:
            closed, _ = self.feed(t)
            if closed is not None:
                yield closed

    def replay(self, ticks: Iterable[Tick]) -> list[MarketBar]:
        out: list[MarketBar] = []
        for t in ticks:
            closed, _ = self.feed(t)
            if closed is not None:
                out.append(closed)
        return out
