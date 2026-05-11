"""Deterministic replay adapter — reads OHLCV from Parquet.

This is the Phase 0 default ingestion path. It MUST produce byte-identical
diagnoses for identical inputs (Appendix S). The adapter therefore:

    - locks NumPy/Python random seeds at construction
    - enforces single-threaded BLAS via env vars
    - reads bars in strict ascending event-time order
    - never injects wall-clock processing time into downstream computation
"""

from __future__ import annotations

import os
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from core.ingestion.base_adapter import BaseAdapter, IngestionEvent
from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL, MarketBar


def lock_determinism(*, seed: int = 0) -> None:
    """Pin every known source of non-determinism. Called by ReplayAdapter."""
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    random.seed(seed)
    np.random.seed(seed)


class ReplayAdapter(BaseAdapter):
    """Read OHLCV from a Parquet file and replay it as IngestionEvents.

    Expected columns:
        timestamp (int64 ns or datetime64 UTC), open, high, low, close, volume

    Optional columns:
        symbol, is_partial
    """

    def __init__(
        self,
        parquet_path: str | Path,
        *,
        symbol: str = DEFAULT_SYMBOL,
        timeframe: Timeframe = Timeframe.ONE_MIN,
        seed: int = 0,
        watermark_tolerance_bars: int = 2,
    ) -> None:
        super().__init__(
            symbol=symbol,
            timeframe=timeframe,
            source=SourceMode.REPLAY,
            watermark_tolerance_bars=watermark_tolerance_bars,
        )
        lock_determinism(seed=seed)
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"replay parquet not found: {self.parquet_path}")
        self._fixed_processing_time = datetime(2026, 1, 1, tzinfo=UTC)

    def _coerce_timestamp(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, np.datetime64):
            ns = int(value.astype("datetime64[ns]").astype("int64"))
            return datetime.fromtimestamp(ns / 1e9, tz=UTC)
        if isinstance(value, int):
            return datetime.fromtimestamp(value / 1e9, tz=UTC)
        raise TypeError(f"unsupported timestamp column dtype: {type(value).__name__}")

    async def _stream(self) -> AsyncIterator[IngestionEvent]:
        table = pq.read_table(self.parquet_path)
        df = table.to_pandas()
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"parquet missing required columns: {sorted(missing)}")
        df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

        last_ts: datetime | None = None
        tf_seconds = self.timeframe.seconds

        for idx, row in df.iterrows():
            event_time = self._coerce_timestamp(row["timestamp"])
            if last_ts is not None:
                gap = (event_time - last_ts).total_seconds()
                if gap > tf_seconds * 1.5:
                    missing_bars = max(int(round(gap / tf_seconds)) - 1, 0)
                    for k in range(1, missing_bars + 1):
                        recovered_ts = last_ts.timestamp() + k * tf_seconds
                        recovered_dt = datetime.fromtimestamp(recovered_ts, tz=UTC)
                        recovered_close = float(df.iloc[max(int(idx) - 1, 0)]["close"])
                        recovered_bar = MarketBar(
                            timestamp=recovered_dt,
                            timeframe=self.timeframe,
                            source=self.source,
                            confidence=0.25,
                            symbol=str(row.get("symbol", self.symbol)),
                            open=recovered_close,
                            high=recovered_close,
                            low=recovered_close,
                            close=recovered_close,
                            volume=0.0,
                            is_partial=False,
                        )
                        yield IngestionEvent(
                            bar=recovered_bar,
                            processing_time=self._fixed_processing_time,
                            event_time=recovered_dt,
                            sequence=0,
                            is_recovered=True,
                            is_partial=False,
                            meta={"reason": "missing_candle_synthetic_fill"},
                        )

            bar = MarketBar(
                timestamp=event_time,
                timeframe=self.timeframe,
                source=self.source,
                confidence=1.0,
                symbol=str(row.get("symbol", self.symbol)),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                is_partial=bool(row.get("is_partial", False)),
            )
            yield IngestionEvent(
                bar=bar,
                processing_time=self._fixed_processing_time,
                event_time=event_time,
                sequence=0,
                is_recovered=False,
                is_partial=bar.is_partial,
            )
            last_ts = event_time
