"""MarketState — the unit of market observation consumed by every engine.

A MarketState carries the current bar plus an immutable tail window of recent
bars sufficient for the longest pathology window in Phase 0 (Wilder ATR_64
needs 64 bars of seed; entropy uses 64 states; we therefore default the tail
to 256 bars to comfortably feed every primitive).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.enums import SourceMode, Timeframe

PositiveFloat = Annotated[float, Field(gt=0.0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]

DEFAULT_SYMBOL: str = "BTCUSDT"


class MarketBar(MSPISSchema):
    """Single OHLCV bar.

    MarketBar inherits MSPISSchema so each bar also carries schema_version,
    timestamp, timeframe, source, confidence (data-quality confidence in [0,1]).
    """

    symbol: str = Field(default=DEFAULT_SYMBOL, min_length=3, max_length=32)
    open: PositiveFloat
    high: PositiveFloat
    low: PositiveFloat
    close: PositiveFloat
    volume: NonNegativeFloat
    is_partial: bool = False

    @field_validator("symbol")
    @classmethod
    def _check_symbol(cls, v: str) -> str:
        v = v.upper().strip()
        if not v.isalnum():
            raise ValueError(f"symbol must be alphanumeric, got {v!r}")
        return v

    def model_post_init(self, _: object) -> None:
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"open {self.open} must lie within [low {self.low}, high {self.high}]")
        if not (self.low <= self.close <= self.high):
            raise ValueError(
                f"close {self.close} must lie within [low {self.low}, high {self.high}]"
            )

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


class MarketState(MSPISSchema):
    """The observable market state at a single instant for a single symbol/timeframe.

    Carries the current bar plus a tail of recent bars (oldest first → most recent last).
    Stale data, partial bars, and watermark violations degrade `data_quality`.
    """

    symbol: str = Field(default=DEFAULT_SYMBOL)
    current_bar: MarketBar
    tail: tuple[MarketBar, ...] = Field(default_factory=tuple)
    data_quality: UnitFloat = 1.0
    is_stale: bool = False
    watermark_lag_seconds: NonNegativeFloat = 0.0

    @field_validator("tail")
    @classmethod
    def _tail_monotonic(cls, v: tuple[MarketBar, ...]) -> tuple[MarketBar, ...]:
        if not v:
            return v
        prev: datetime | None = None
        for bar in v:
            if prev is not None and bar.timestamp <= prev:
                raise ValueError("MarketState.tail must be strictly time-monotonic ascending")
            prev = bar.timestamp
        return v

    def model_post_init(self, _: object) -> None:
        if self.tail and self.tail[-1].timestamp >= self.current_bar.timestamp:
            raise ValueError("MarketState.tail must precede current_bar in time")
        for bar in self.tail:
            if bar.timeframe != self.timeframe:
                raise ValueError(
                    f"MarketState.tail bar timeframe {bar.timeframe} != state timeframe {self.timeframe}"
                )

    @property
    def window(self) -> tuple[MarketBar, ...]:
        return (*self.tail, self.current_bar)

    @property
    def closes(self) -> tuple[float, ...]:
        return tuple(b.close for b in self.window)

    @property
    def highs(self) -> tuple[float, ...]:
        return tuple(b.high for b in self.window)

    @property
    def lows(self) -> tuple[float, ...]:
        return tuple(b.low for b in self.window)

    @property
    def volumes(self) -> tuple[float, ...]:
        return tuple(b.volume for b in self.window)

    def __len__(self) -> int:
        return len(self.tail) + 1


def empty_market_state(
    *,
    timestamp: datetime,
    timeframe: Timeframe,
    source: SourceMode,
    bar: MarketBar,
) -> MarketState:
    """Convenience constructor for a single-bar state (cold-start)."""
    return MarketState(
        timestamp=timestamp,
        timeframe=timeframe,
        source=source,
        confidence=1.0,
        current_bar=bar,
    )
