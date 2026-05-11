"""Numerical-precision policy. Closes audit gap #45.

Aquila probabilistic math runs in float64 but every output is clamped and
NaN/Inf-guarded. Decimal context is used only for price/size arithmetic via
`as_decimal()`.
"""

from __future__ import annotations

import math
from decimal import Decimal, getcontext

_DEFAULT_PREC = 28
getcontext().prec = _DEFAULT_PREC


def safe_prob(x: float) -> float:
    """Clamp to [0, 1]; coerce NaN/Inf to 0.0."""
    if not isinstance(x, (int, float)):
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def safe_float(x: float, default: float = 0.0) -> float:
    if not isinstance(x, (int, float)):
        return default
    if math.isnan(x) or math.isinf(x):
        return default
    return float(x)


def as_decimal(x: float | str | Decimal) -> Decimal:
    return Decimal(str(x))
