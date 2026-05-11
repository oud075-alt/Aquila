"""Binance (spot) data feed implemented via the CCXT library.

If CCXT is not installed or credentials are missing the feed falls back to
the synthetic generator so that the rest of the pipeline can run in CI or
on machines without live API access.
"""

from __future__ import annotations

import asyncio
from typing import List

from brain.logging_utils import get_logger
from brain.schemas import Candle
from brain.sensory.base import DataFeed, FeedError
from config import get_api_keys

try:  # ccxt is an optional runtime dependency for live data
    import ccxt  # type: ignore
except Exception:  # pragma: no cover - exercised only when ccxt missing
    ccxt = None  # type: ignore


_BINANCE_TIMEFRAMES = {
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}


class BinanceFeed(DataFeed):
    """Async wrapper around CCXT for Binance spot data."""

    name = "binance"

    def __init__(self, symbol: str, timeframe: str = "1m"):
        super().__init__(symbol=symbol, timeframe=timeframe)
        self.log = get_logger("mspis.sensory.binance")
        self._client = None
        self._connected = False
        keys = get_api_keys()
        self._use_testnet = keys.binance_use_testnet
        self._api_key = keys.binance_api_key
        self._api_secret = keys.binance_api_secret

    async def connect(self) -> bool:
        if ccxt is None:
            self.log.warning("ccxt not installed — Binance feed will use synthetic fallback")
            return False
        if self.timeframe not in _BINANCE_TIMEFRAMES:
            self.log.warning("Timeframe %s is not natively supported by Binance", self.timeframe)
        try:
            cls = ccxt.binance
            options = {
                "enableRateLimit": True,
                "timeout": 15000,
            }
            if self._api_key:
                options["apiKey"] = self._api_key
                options["secret"] = self._api_secret or ""
            self._client = cls(options)
            if self._use_testnet and hasattr(self._client, "set_sandbox_mode"):
                self._client.set_sandbox_mode(True)
            self._connected = True
            return True
        except Exception as e:
            self.log.warning("Binance connect failed (%s); falling back to synthetic", e)
            self._connected = False
            return False

    async def fetch_candles(self, lookback: int) -> List[Candle]:
        if self._client is None and ccxt is not None:
            await self.connect()

        if self._client is None:
            return self._synthetic_candles(lookback, seed=42)

        loop = asyncio.get_running_loop()

        def _do_fetch():
            try:
                return self._client.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=lookback)
            except Exception as e:
                raise FeedError(f"binance.fetch_ohlcv failed: {e}") from e

        try:
            rows = await loop.run_in_executor(None, _do_fetch)
        except FeedError as e:
            self.log.warning("%s — using synthetic data for this poll", e)
            return self._synthetic_candles(lookback, seed=42)

        candles: List[Candle] = []
        for row in rows:
            c = self._parse_ohlcv_row(row)
            if c is not None:
                candles.append(c)
        if not candles:
            return self._synthetic_candles(lookback, seed=42)
        return candles
