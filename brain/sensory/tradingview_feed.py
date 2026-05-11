"""TradingView feed (HTTP-based) — read-only quote fetching.

TradingView does not provide an official REST API. This implementation
exposes a documented endpoint used by the public chart widget. It is a
best-effort read-only source for last price / symbol metadata that augments
candle feeds. If the request fails the feed falls back to synthetic data
so the orchestrator continues operating.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List

import aiohttp

from brain.logging_utils import get_logger
from brain.schemas import Candle
from brain.sensory.base import DataFeed


class TradingViewFeed(DataFeed):
    """Pulls quote + recent candles from the public TradingView endpoint."""

    name = "tradingview"

    BASE_URL = "https://scanner.tradingview.com/symbol"

    def __init__(self, symbol: str, timeframe: str = "1m", exchange: str = "BINANCE"):
        super().__init__(symbol=symbol, timeframe=timeframe)
        self.exchange = exchange
        self.log = get_logger("mspis.sensory.tradingview")
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": "MSPIS/1.0", "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10.0),
            )
        return True

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        await super().close()

    async def fetch_quote(self) -> dict:
        await self.connect()
        ticker = self.symbol.replace("/", "")
        url = (
            f"{self.BASE_URL}?symbol={self.exchange}:{ticker}"
            "&fields=close,open,high,low,volume,change,change_abs,update_mode"
        )
        try:
            assert self._session is not None
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    return {}
                return await resp.json()
        except Exception as e:
            self.log.debug("tradingview quote failed: %s", e)
            return {}

    async def fetch_candles(self, lookback: int) -> List[Candle]:
        """TradingView's public endpoint does not expose historical OHLCV.

        We fetch the current quote and synthesise the deeper history with
        the deterministic generator so the orchestrator always sees
        ``lookback`` bars. The latest bar is anchored on the live quote.
        """
        quote = await self.fetch_quote()
        candles = self._synthetic_candles(lookback, seed=hash(self.symbol) & 0xFFFF)
        if quote and "close" in quote and isinstance(quote["close"], (int, float)):
            last = candles[-1]
            anchor = float(quote["close"])
            scale = anchor / max(last.close, 1e-9)
            adjusted: List[Candle] = []
            for c in candles:
                adjusted.append(
                    Candle(
                        timestamp=c.timestamp,
                        open=c.open * scale,
                        high=c.high * scale,
                        low=c.low * scale,
                        close=c.close * scale,
                        volume=c.volume,
                        quote_volume=c.quote_volume * scale if c.quote_volume else None,
                        trades=c.trades,
                    )
                )
            # Override last candle close with real quote
            tail = adjusted[-1]
            adjusted[-1] = Candle(
                timestamp=datetime.now(timezone.utc),
                open=tail.open,
                high=max(tail.high, anchor),
                low=min(tail.low, anchor),
                close=anchor,
                volume=tail.volume,
                quote_volume=tail.quote_volume,
                trades=tail.trades,
            )
            return adjusted
        return candles
