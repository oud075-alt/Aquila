"""Candle stream multiplexer.

Aggregates one or more :class:`DataFeed` instances into a single asynchronous
stream of :class:`Candle` objects. Maintains a rolling cache so the
orchestrator can synchronously inspect history at diagnosis time.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Awaitable, Callable, Deque, Dict, List, Optional, Tuple

from brain.logging_utils import get_logger
from brain.schemas import Candle
from brain.sensory.base import DataFeed


class CandleStream:
    """Multi-feed candle aggregator with bounded rolling history."""

    def __init__(self, history: int = 2000):
        self.log = get_logger("mspis.sensory.candle_stream")
        self.history = history
        self._feeds: Dict[Tuple[str, str, str], DataFeed] = {}
        self._buffers: Dict[Tuple[str, str, str], Deque[Candle]] = defaultdict(
            lambda: deque(maxlen=self.history)
        )
        self._listeners: List[Callable[[str, str, str, Candle], Awaitable[None]]] = []
        self._tasks: List[asyncio.Task] = []
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Feed management
    # ------------------------------------------------------------------
    def register_feed(self, feed: DataFeed) -> None:
        key = (feed.name, feed.symbol, feed.timeframe)
        self._feeds[key] = feed

    def add_listener(self, fn: Callable[[str, str, str, Candle], Awaitable[None]]) -> None:
        self._listeners.append(fn)

    def snapshot(self, source: str, symbol: str, timeframe: str) -> List[Candle]:
        return list(self._buffers.get((source, symbol, timeframe), deque()))

    def latest(self, source: str, symbol: str, timeframe: str) -> Optional[Candle]:
        buf = self._buffers.get((source, symbol, timeframe))
        return buf[-1] if buf else None

    # ------------------------------------------------------------------
    # Bootstrap + run
    # ------------------------------------------------------------------
    async def bootstrap(self, lookback: int) -> None:
        for key, feed in list(self._feeds.items()):
            try:
                bars = await feed.fetch_candles(lookback)
            except Exception as e:
                self.log.warning("Bootstrap failure for %s: %s", key, e)
                bars = []
            for b in bars:
                self._buffers[key].append(b)

    async def start(self) -> None:
        await self.bootstrap(self.history)
        loop = asyncio.get_running_loop()
        for key, feed in self._feeds.items():
            async def _on_candle(c: Candle, _key=key):
                await self._handle_new(_key, c)

            task = loop.create_task(feed.stream(_on_candle))
            self._tasks.append(task)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        for key, feed in self._feeds.items():
            try:
                await feed.close()
            except Exception:
                pass
        self._tasks.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _handle_new(self, key: Tuple[str, str, str], candle: Candle) -> None:
        async with self._lock:
            buf = self._buffers[key]
            if buf and buf[-1].timestamp >= candle.timestamp:
                # Update in place if same bar tick (intra-bar tick update)
                if buf[-1].timestamp == candle.timestamp:
                    buf[-1] = candle
                return
            buf.append(candle)
        for fn in list(self._listeners):
            try:
                await fn(*key, candle)
            except Exception as e:
                self.log.debug("listener error: %s", e)
