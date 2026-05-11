"""MetaTrader 5 (Windows broker terminal) data feed.

The `MetaTrader5` Python bindings only ship on Windows. On other operating
systems the import is guarded and the feed transparently falls back to the
synthetic generator. This guarantees the rest of the pipeline runs in any
environment.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from brain.logging_utils import get_logger
from brain.schemas import Candle
from brain.sensory.base import DataFeed
from config import get_api_keys

try:  # platform-dependent
    import MetaTrader5 as mt5  # type: ignore
except Exception:
    mt5 = None  # type: ignore


_MT5_TIMEFRAME_MAP = {
    "1m": 1, "2m": 2, "3m": 3, "4m": 4, "5m": 5, "6m": 6, "10m": 10,
    "12m": 12, "15m": 15, "20m": 20, "30m": 30,
    "1h": 60, "2h": 120, "3h": 180, "4h": 240, "6h": 360, "8h": 480,
    "12h": 720, "1d": 1440, "1w": 10080, "1M": 43200,
}


class MT5Feed(DataFeed):
    """Async wrapper around the MT5 terminal API."""

    name = "mt5"

    def __init__(self, symbol: str, timeframe: str = "1m"):
        super().__init__(symbol=symbol, timeframe=timeframe)
        self.log = get_logger("mspis.sensory.mt5")
        self._connected: bool = False
        self._creds = get_api_keys()

    async def connect(self) -> bool:
        if mt5 is None:
            self.log.warning("MetaTrader5 not available on this platform")
            return False
        loop = asyncio.get_running_loop()

        def _init() -> bool:
            kwargs = {}
            if self._creds.mt5_path:
                kwargs["path"] = self._creds.mt5_path
            ok = mt5.initialize(**kwargs)
            if not ok:
                return False
            if self._creds.has_mt5():
                ok = mt5.login(
                    int(self._creds.mt5_login) if self._creds.mt5_login else 0,
                    password=self._creds.mt5_password or "",
                    server=self._creds.mt5_server or "",
                )
                if not ok:
                    return False
            return mt5.symbol_select(self.symbol, True) or True

        try:
            self._connected = bool(await loop.run_in_executor(None, _init))
        except Exception as e:
            self.log.warning("MT5 init failed: %s", e)
            self._connected = False
        return self._connected

    async def fetch_candles(self, lookback: int) -> List[Candle]:
        if mt5 is None or not self._connected:
            await self.connect()
        if not self._connected or mt5 is None:
            return self._synthetic_candles(lookback, seed=7)

        loop = asyncio.get_running_loop()
        tf_minutes = _MT5_TIMEFRAME_MAP.get(self.timeframe, 1)
        tf_const = getattr(mt5, f"TIMEFRAME_M{tf_minutes}", None) or getattr(mt5, "TIMEFRAME_M1")

        def _fetch():
            try:
                return mt5.copy_rates_from_pos(self.symbol, tf_const, 0, lookback)
            except Exception:
                return None

        rows: Optional[list] = await loop.run_in_executor(None, _fetch)
        if rows is None or len(rows) == 0:
            return self._synthetic_candles(lookback, seed=7)

        candles: List[Candle] = []
        for r in rows:
            try:
                ts = datetime.fromtimestamp(float(r["time"]), tz=timezone.utc)
                candles.append(
                    Candle(
                        timestamp=ts,
                        open=float(r["open"]),
                        high=float(r["high"]),
                        low=float(r["low"]),
                        close=float(r["close"]),
                        volume=float(r["tick_volume"]),
                    )
                )
            except Exception:
                continue
        return candles or self._synthetic_candles(lookback, seed=7)

    async def close(self) -> None:
        if mt5 is not None and self._connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
        await super().close()
