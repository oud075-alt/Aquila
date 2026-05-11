from __future__ import annotations

import math
from collections import deque

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.numeric import safe_float
from aquila.core.types import LayerName
from aquila.primitives.interfaces import PrimitiveMetricsService
from aquila.primitives.schemas import PrimitiveBar, PrimitiveSnapshot


class PrimitiveMetricsLayer(PrimitiveMetricsService):
    layer_name = LayerName.PRIMITIVES

    def __init__(self, window: int = 50) -> None:
        super().__init__()
        self._window = window
        self._bars: deque[PrimitiveBar] = deque(maxlen=window)

    def append_bar(self, bar: PrimitiveBar) -> None:
        self._bars.append(bar)

    def process(self, payload: PrimitiveBar, ctx: LayerContext) -> LayerOutput[PrimitiveSnapshot]:
        self.append_bar(payload)
        bars = list(self._bars)
        if len(bars) < 2:
            snap = PrimitiveSnapshot(bars_seen=len(bars), last_close=payload.close)
            return self.wrap(payload=snap, ctx=ctx, confidence=0.05, visibility="degraded")

        closes = [b.close for b in bars]
        returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
        mean_r = sum(returns) / max(1, len(returns))
        var_r = sum((r - mean_r) ** 2 for r in returns) / max(1, len(returns))
        rvol = math.sqrt(var_r) if var_r > 0 else 0.0

        vols = [b.volume for b in bars]
        vmean = sum(vols) / len(vols)
        vstd = math.sqrt(sum((v - vmean) ** 2 for v in vols) / len(vols)) if len(vols) > 1 else 0.0
        vz = (payload.volume - vmean) / vstd if vstd > 0 else 0.0

        last = payload
        prev_close = bars[-2].close if len(bars) >= 2 else payload.open
        ret_pct = (last.close - prev_close) / prev_close if prev_close > 0 else 0.0
        range_pct = last.range / last.close if last.close > 0 else 0.0
        body_ratio = last.body / last.range if last.range > 0 else 0.0
        uw = last.upper_wick / last.range if last.range > 0 else 0.0
        lw = last.lower_wick / last.range if last.range > 0 else 0.0

        snap = PrimitiveSnapshot(
            bars_seen=len(bars),
            last_close=last.close,
            realized_vol=safe_float(rvol),
            return_pct=safe_float(ret_pct),
            range_pct=safe_float(range_pct),
            body_ratio=safe_float(body_ratio),
            upper_wick_ratio=safe_float(uw),
            lower_wick_ratio=safe_float(lw),
            volume_z=safe_float(vz),
            features={"window": float(self._window), "n": float(len(bars))},
        )
        confidence = min(1.0, len(bars) / self._window)
        visibility = "full" if len(bars) >= self._window // 2 else "partial"
        return self.wrap(payload=snap, ctx=ctx, confidence=confidence, visibility=visibility)
