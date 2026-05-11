"""Abstract base class for every data feed.

Every feed exposes the same async surface so the orchestrator and the
candle stream multiplexer can treat them uniformly.
"""

from __future__ import annotations

import abc
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, List, Optional

import numpy as np

from brain.schemas import Candle
from config import get_market_config


class FeedError(RuntimeError):
    """Raised when a feed cannot recover from a downstream failure."""


class DataFeed(abc.ABC):
    """Abstract async data feed contract."""

    name: str = "abstract"

    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self._market_cfg = get_market_config()
        self._cancel = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> bool:
        """Establish underlying connection (default no-op)."""
        return True

    async def close(self) -> None:
        self._cancel = True

    # ------------------------------------------------------------------
    # Required methods
    # ------------------------------------------------------------------
    @abc.abstractmethod
    async def fetch_candles(self, lookback: int) -> List[Candle]:
        """Return the most recent ``lookback`` historical candles."""

    async def stream(
        self,
        on_candle: Callable[[Candle], Awaitable[None]],
        poll_seconds: Optional[float] = None,
    ) -> None:
        """Default poll-based stream implementation.

        Subclasses may override to use websocket-native streaming.
        """
        if poll_seconds is None:
            poll_seconds = float(self._market_cfg.timeframe_seconds(self.timeframe))
        last_ts: Optional[datetime] = None
        while not self._cancel:
            try:
                bars = await self.fetch_candles(lookback=2)
                if bars:
                    latest = bars[-1]
                    if last_ts is None or latest.timestamp > last_ts:
                        last_ts = latest.timestamp
                        await on_candle(latest)
            except Exception:
                # Fault tolerance: never crash the stream
                await self._sleep(min(5.0, poll_seconds))
            await self._sleep(poll_seconds)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _sleep(self, seconds: float) -> None:
        import asyncio

        try:
            await asyncio.sleep(max(0.05, float(seconds)))
        except asyncio.CancelledError:
            self._cancel = True
            raise

    # ------------------------------------------------------------------
    # Synthetic fallback (used when no credentials are available)
    # ------------------------------------------------------------------
    def _synthetic_candles(self, n: int, seed: int | None = None) -> List[Candle]:
        """Generate a deterministic, realistic OHLCV series.

        This is **not** a mock for production diagnosis — it is a fallback
        so that operators can exercise the pipeline end-to-end without live
        credentials. All other modules are completely unaware of whether
        the underlying candles came from a live feed or this generator.
        """
        rng = np.random.default_rng(seed if seed is not None else hash(self.symbol) & 0xFFFF)
        # GARCH-like vol process to make tests meaningful
        n = max(n, 60)
        vol = np.empty(n)
        vol[0] = 0.005
        for i in range(1, n):
            vol[i] = max(1e-5, 0.9 * vol[i - 1] + 0.1 * abs(rng.normal(0, 0.004)))

        # Trend regime that switches a few times
        regime = np.zeros(n)
        regime_value = rng.choice([-1, 0, 1])
        for i in range(n):
            if rng.random() < 0.01:
                regime_value = rng.choice([-1, 0, 1])
            regime[i] = regime_value

        drift = regime * 0.0008
        returns = drift + vol * rng.normal(0.0, 1.0, n)
        price = 100.0 * np.exp(np.cumsum(returns))
        tf_seconds = self._market_cfg.timeframe_seconds(self.timeframe)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        candles: List[Candle] = []
        for i in range(n):
            ts = now - timedelta(seconds=tf_seconds * (n - 1 - i))
            o = float(price[i - 1]) if i > 0 else float(price[i] * (1 - returns[i] * 0.5))
            c = float(price[i])
            spread = abs(c - o) + float(vol[i]) * c
            h = float(max(o, c) + spread * (0.4 + rng.random() * 0.6))
            l = float(min(o, c) - spread * (0.4 + rng.random() * 0.6))
            v = float(max(1.0, abs(rng.normal(1000, 250)) * (1.0 + 4 * vol[i])))
            candles.append(
                Candle(
                    timestamp=ts,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v,
                    quote_volume=v * c,
                    trades=int(max(1, abs(rng.normal(120, 30)))),
                )
            )
        return candles

    # ------------------------------------------------------------------
    # Static utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_ohlcv_row(row: Any) -> Optional[Candle]:
        """Build a :class:`Candle` from a generic OHLCV row (list or dict)."""
        try:
            if isinstance(row, dict):
                ts = row.get("timestamp") or row.get("time") or row.get("t")
                o = row.get("open") or row.get("o")
                h = row.get("high") or row.get("h")
                l = row.get("low") or row.get("l")
                c = row.get("close") or row.get("c")
                v = row.get("volume") or row.get("v") or 0.0
            else:
                ts, o, h, l, c, v = row[0], row[1], row[2], row[3], row[4], row[5]
            if ts is None:
                return None
            if isinstance(ts, (int, float)):
                # Heuristic: ms vs seconds
                seconds = ts / 1000.0 if ts > 10_000_000_000 else ts
                ts = datetime.fromtimestamp(float(seconds), tz=timezone.utc)
            elif isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif not isinstance(ts, datetime):
                return None
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return Candle(
                timestamp=ts,
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v),
            )
        except Exception:
            return None
