"""Context manager — per-(symbol, timeframe) context isolation + recent-state cache.

Each tracked stream owns:
    - an OHLCV pipeline (rolling MarketState window)
    - the most recent MarketState
    - the most recent pathology / regime / contradiction / diagnosis

The context manager surfaces snapshots needed by multi-timeframe fusion
(Phase 2). In Phase 0 only the 1m timeframe is active, but the data
structures are timeframe-keyed and ready to host higher TFs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from core.ingestion.ohlcv_pipeline import OHLCVPipeline
from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL, MarketState
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState
from core.schemas.timeframe_context import TimeframeSnapshot


@dataclass(slots=True)
class StreamContext:
    """Per-(symbol, timeframe) live context."""

    symbol: str
    timeframe: Timeframe
    pipeline: OHLCVPipeline
    market_state: MarketState | None = None
    pathology: PathologyReport | None = None
    regime: RegimeState | None = None
    last_update: datetime | None = None
    history: list[float] = field(default_factory=list)

    def snapshot(self) -> TimeframeSnapshot | None:
        if self.pathology is None or self.regime is None or self.market_state is None:
            return None
        return TimeframeSnapshot(
            timestamp=self.pathology.timestamp,
            timeframe=self.timeframe,
            source=self.market_state.source,
            confidence=self.pathology.confidence,
            structural_state=self.pathology.structural_state,
            regime=self.regime.regime,
            instability_score=self.pathology.instability_score,
            structural_health=self.pathology.structural_health,
            is_stale=self.market_state.is_stale,
        )


class ContextManager:
    """Holds per-stream context. Single-symbol in Phase 0 (Appendix Q)."""

    def __init__(
        self,
        *,
        symbol: str = DEFAULT_SYMBOL,
        source: SourceMode = SourceMode.REPLAY,
        timeframes: tuple[Timeframe, ...] = (Timeframe.ONE_MIN,),
        tail_length: int = 256,
    ) -> None:
        self.symbol = symbol.upper()
        self.source = source
        self._lock = asyncio.Lock()
        self._streams: dict[tuple[str, Timeframe], StreamContext] = {}
        for tf in timeframes:
            key = (self.symbol, tf)
            self._streams[key] = StreamContext(
                symbol=self.symbol,
                timeframe=tf,
                pipeline=OHLCVPipeline(timeframe=tf, source=source, symbol=self.symbol, tail_length=tail_length),
            )

    def stream(self, *, timeframe: Timeframe, symbol: str | None = None) -> StreamContext:
        sym = (symbol or self.symbol).upper()
        key = (sym, timeframe)
        ctx = self._streams.get(key)
        if ctx is None:
            raise KeyError(f"no stream registered for {key}")
        return ctx

    def all_snapshots(self) -> list[TimeframeSnapshot]:
        out: list[TimeframeSnapshot] = []
        for ctx in self._streams.values():
            snap = ctx.snapshot()
            if snap is not None:
                out.append(snap)
        out.sort(key=lambda s: s.timeframe.order)
        return out

    @property
    def active_timeframes(self) -> tuple[Timeframe, ...]:
        return tuple(sorted({k[1] for k in self._streams}, key=lambda t: t.order))
