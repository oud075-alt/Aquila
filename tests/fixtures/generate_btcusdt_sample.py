"""Generate a deterministic BTCUSDT 1m sample parquet for replay tests.

Uses a fixed seed and a simple geometric random walk plus a regime shift to
exercise pathology primitives across multiple structural states.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def generate(num_bars: int = 512, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
    times = (base + np.arange(num_bars) * 60.0) * 1_000_000_000
    timestamps = pd.to_datetime(times.astype("int64"), unit="ns", utc=True)

    drift = np.concatenate(
        [
            rng.normal(0.0, 0.0008, size=num_bars // 4),
            rng.normal(0.0005, 0.0006, size=num_bars // 4),
            rng.normal(-0.0006, 0.0014, size=num_bars // 4),
            rng.normal(0.0, 0.0004, size=num_bars - 3 * (num_bars // 4)),
        ]
    )
    log_returns = drift
    price = 50_000.0 * np.exp(np.cumsum(log_returns))

    opens = np.concatenate([[price[0]], price[:-1]])
    closes = price
    ranges = np.abs(rng.normal(0.0, 0.0015, size=num_bars)) * closes + 1.0
    highs = np.maximum(opens, closes) + ranges * 0.5
    lows = np.minimum(opens, closes) - ranges * 0.5
    lows = np.maximum(lows, 1.0)
    volumes = np.abs(rng.normal(120.0, 35.0, size=num_bars)) + 1.0

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens.astype(float),
            "high": highs.astype(float),
            "low": lows.astype(float),
            "close": closes.astype(float),
            "volume": volumes.astype(float),
            "symbol": "BTCUSDT",
        }
    )


def write_default(path: Path | None = None) -> Path:
    target = path or Path(__file__).with_name("btcusdt_1m_sample.parquet")
    df = generate()
    df.to_parquet(target, engine="pyarrow", index=False)
    return target


if __name__ == "__main__":
    p = write_default()
    print(f"wrote {p} ({p.stat().st_size} bytes)")  # noqa: T201
    assert math.isfinite(generate(8).close.iloc[-1])
