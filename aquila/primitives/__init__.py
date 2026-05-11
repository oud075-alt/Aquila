"""Layer 1 — Primitive Metrics Layer.

Computes low-level structural primitives from a rolling window of OHLCV:
range, body, wick asymmetry, return, log-return, realized volatility,
volume z-score. These are the raw inputs to Layer 2 (Structural Diagnosis).

The prompt declared this layer "already exists"; the actual repository was
empty, so we provide a minimal-but-functional implementation that satisfies
the same surface contract.
"""

from aquila.primitives.service import PrimitiveMetricsLayer
from aquila.primitives.schemas import PrimitiveBar, PrimitiveSnapshot

__all__ = ["PrimitiveMetricsLayer", "PrimitiveBar", "PrimitiveSnapshot"]
