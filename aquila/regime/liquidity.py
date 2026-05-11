from __future__ import annotations

from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.regime.interfaces import RegimeDetector
from aquila.regime.schemas import RegimeKind


class LiquidityRegimeDetector(RegimeDetector):
    """Heuristic liquidity proxy: high range with low volume = thin book.

    Real implementations would consume order-book / tape data from Layer 0.
    """

    def detect(self, *, primitives: PrimitiveSnapshot, structural=None) -> RegimeKind:
        if primitives is None:
            return RegimeKind.DEEP_LIQUIDITY
        if primitives.range_pct > 0.01 and primitives.volume_z < -0.3:
            return RegimeKind.THIN_LIQUIDITY
        return RegimeKind.DEEP_LIQUIDITY
