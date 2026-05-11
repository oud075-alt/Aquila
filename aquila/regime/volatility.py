from __future__ import annotations

from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.regime.interfaces import RegimeDetector
from aquila.regime.schemas import RegimeKind


class VolatilityRegimeDetector(RegimeDetector):
    def __init__(self, low: float = 0.005, high: float = 0.02) -> None:
        self.low, self.high = low, high

    def detect(self, *, primitives: PrimitiveSnapshot, structural=None) -> RegimeKind:
        v = primitives.realized_vol if primitives else 0.0
        if v < self.low:
            return RegimeKind.LOW_VOL
        if v > self.high:
            return RegimeKind.HIGH_VOL
        return RegimeKind.NORMAL_VOL
