from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PrimitiveBar(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def range(self) -> float:
        return max(0.0, self.high - self.low)

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return max(0.0, self.high - max(self.open, self.close))

    @property
    def lower_wick(self) -> float:
        return max(0.0, min(self.open, self.close) - self.low)


class PrimitiveSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    bars_seen: int = 0
    last_close: float = 0.0
    realized_vol: float = 0.0
    return_pct: float = 0.0
    range_pct: float = 0.0
    body_ratio: float = 0.0
    upper_wick_ratio: float = 0.0
    lower_wick_ratio: float = 0.0
    volume_z: float = 0.0
    features: dict[str, float] = Field(default_factory=dict)
