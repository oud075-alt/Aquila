"""Deterministic synthetic bar generator used to materialise
``tests/data/synthetic_bars_seed42.jsonl``.

Two regimes — calm low-vol vs. wide high-vol — switch every 500 bars to
exercise the detector across distribution changes. The output is bar-
closed OHLCV; intra-bar dynamics are NOT modelled (that's a different
test bench).

Run with:

    python -m tests.data.generate_synthetic_seed42 \\
        --out tests/data/synthetic_bars_seed42.jsonl
"""

from __future__ import annotations

import argparse
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aquila.primitives.schemas import PrimitiveBar


def _generate(n: int = 2000, seed: int = 42) -> list[PrimitiveBar]:
    rng = random.Random(seed)
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    bars: list[PrimitiveBar] = []
    for i in range(n):
        regime_high = (i // 500) % 2 == 1
        sigma = 0.45 if regime_high else 0.10
        drift = 0.0
        move = rng.gauss(drift, sigma)
        high = price + abs(move) + abs(rng.gauss(0, sigma * 0.4))
        low = price - abs(move) - abs(rng.gauss(0, sigma * 0.4))
        close = price + move

        base_vol = 12.0 if regime_high else 8.0
        if regime_high and abs(move) > sigma * 1.8:
            vol = base_vol * 0.4 + rng.uniform(0, 0.5)
        else:
            vol = max(0.1, base_vol + rng.gauss(0, 1.5))

        bars.append(PrimitiveBar(
            timestamp=t0 + timedelta(minutes=i),
            open=price, high=high, low=low, close=close, volume=vol,
        ))
        price = max(1.0, close)
    return bars


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    bars = _generate(n=args.n, seed=args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for b in bars:
            f.write(b.model_dump_json() + "\n")
    print(f"wrote {len(bars)} bars to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
