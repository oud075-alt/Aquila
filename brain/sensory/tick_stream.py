"""Tick stream — async micro-structure event source.

The :class:`TickStream` consumes raw tick events from any data feed (or
external websocket) and exposes them as an awaitable iterator. It also
maintains light-weight rolling statistics for the orchestrator to query.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Awaitable, Callable, Deque, Dict, List, Optional


@dataclass
class TickEvent:
    timestamp: datetime
    price: float
    volume: float = 0.0
    side: Optional[str] = None  # "buy" | "sell" | None
    aggressor: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "volume": self.volume,
            "side": self.side,
            "aggressor": self.aggressor,
        }


@dataclass
class TickRollingStats:
    """Cheap rolling moments computed online."""

    window: int = 500
    prices: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    volumes: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    count: int = 0

    def update(self, t: TickEvent) -> None:
        self.prices.append(t.price)
        self.volumes.append(t.volume)
        self.count += 1
        if t.side == "buy":
            self.buy_volume += t.volume
        elif t.side == "sell":
            self.sell_volume += t.volume

    def imbalance(self) -> float:
        denom = self.buy_volume + self.sell_volume
        if denom < 1e-12:
            return 0.0
        return float((self.buy_volume - self.sell_volume) / denom)

    def vwap(self) -> float:
        if not self.prices:
            return 0.0
        s = sum(p * v for p, v in zip(self.prices, self.volumes))
        v = sum(self.volumes) or 1e-9
        return float(s / v)


class TickStream:
    """Async producer/consumer queue for tick events."""

    def __init__(self, max_buffer: int = 5000, window: int = 500):
        self._queue: asyncio.Queue[TickEvent] = asyncio.Queue(maxsize=max_buffer)
        self.stats = TickRollingStats(window=window)
        self._listeners: List[Callable[[TickEvent], Awaitable[None]]] = []

    def add_listener(self, fn: Callable[[TickEvent], Awaitable[None]]) -> None:
        self._listeners.append(fn)

    async def publish(self, tick: TickEvent) -> None:
        self.stats.update(tick)
        try:
            self._queue.put_nowait(tick)
        except asyncio.QueueFull:
            try:
                _ = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            await self._queue.put(tick)
        for fn in list(self._listeners):
            try:
                await fn(tick)
            except Exception:
                continue

    async def consume(self) -> AsyncIterator[TickEvent]:
        while True:
            tick = await self._queue.get()
            yield tick

    def snapshot(self) -> Dict:
        return {
            "count": self.stats.count,
            "vwap": self.stats.vwap(),
            "imbalance": self.stats.imbalance(),
            "buy_volume": self.stats.buy_volume,
            "sell_volume": self.stats.sell_volume,
            "last_price": self.stats.prices[-1] if self.stats.prices else None,
        }

    def synthesise_from_candle(self, candle) -> List[TickEvent]:
        """Derive plausible ticks from a single OHLC bar (for synthetic mode)."""
        ts = candle.timestamp
        seq = [candle.open, candle.high, candle.low, candle.close]
        ticks: List[TickEvent] = []
        per_tick_vol = max(candle.volume / 4.0, 1.0)
        for i, p in enumerate(seq):
            side = "buy" if p >= candle.open else "sell"
            ticks.append(
                TickEvent(
                    timestamp=ts,
                    price=float(p),
                    volume=float(per_tick_vol),
                    side=side,
                    aggressor=side,
                )
            )
        return ticks
