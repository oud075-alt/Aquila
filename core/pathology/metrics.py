"""Canonical metric primitives shared by every pathology module (ADR-0002).

All functions are pure, deterministic, and consume plain NumPy arrays.
Higher-level pathology modules call into these — they MUST NOT redefine
these metrics ad hoc (this is enforced by code review and by importing
from here in every primitive).
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]

EPS: float = 1e-12


def _as_float64(arr: npt.ArrayLike) -> FloatArray:
    out = np.asarray(arr, dtype=np.float64)
    if out.ndim != 1:
        raise ValueError(f"expected 1-D array, got shape {out.shape}")
    return out


def wilder_atr(highs: npt.ArrayLike, lows: npt.ArrayLike, closes: npt.ArrayLike, *, period: int = 64) -> float:
    """Wilder's ATR over the trailing `period` bars (returns the latest ATR value)."""
    h = _as_float64(highs)
    lo = _as_float64(lows)
    c = _as_float64(closes)
    if not (len(h) == len(lo) == len(c)):
        raise ValueError("highs/lows/closes must be same length")
    if len(c) < period + 1:
        return float(np.mean(h - lo)) if len(h) > 0 else 0.0
    tr = np.maximum.reduce(
        [
            h[1:] - lo[1:],
            np.abs(h[1:] - c[:-1]),
            np.abs(lo[1:] - c[:-1]),
        ]
    )
    atr = float(np.mean(tr[:period]))
    for x in tr[period:]:
        atr = (atr * (period - 1) + float(x)) / period
    return max(atr, EPS)


def rolling_range(highs: npt.ArrayLike, lows: npt.ArrayLike) -> float:
    """Per-bar range of the LAST bar (ADR-0002)."""
    h = _as_float64(highs)
    lo = _as_float64(lows)
    if len(h) == 0:
        return 0.0
    return float(h[-1] - lo[-1])


def trend_slope(closes: npt.ArrayLike, *, window: int = 32) -> float:
    """OLS slope of `close` over the last `window` bars, normalized by mean close."""
    c = _as_float64(closes)
    if len(c) < 2:
        return 0.0
    seg = c[-window:]
    n = len(seg)
    x = np.arange(n, dtype=np.float64)
    x_mean = x.mean()
    y_mean = seg.mean()
    denom = float(((x - x_mean) ** 2).sum())
    if denom <= EPS:
        return 0.0
    slope = float(((x - x_mean) * (seg - y_mean)).sum() / denom)
    return slope / max(abs(float(y_mean)), EPS)


def directional_efficiency(closes: npt.ArrayLike, *, window: int = 32) -> float:
    """Kaufman efficiency ratio over the last `window` bars."""
    c = _as_float64(closes)
    if len(c) < 2:
        return 0.0
    seg = c[-window:]
    net = abs(float(seg[-1] - seg[0]))
    gross = float(np.abs(np.diff(seg)).sum())
    if gross <= EPS:
        return 0.0
    return min(1.0, max(0.0, net / gross))


def robust_zscore(value: float, history: npt.ArrayLike, *, window: int = 64) -> float:
    """Z-score of `value` against the trailing `window` of `history` via median / MAD."""
    h = _as_float64(history)
    if len(h) == 0:
        return 0.0
    seg = h[-window:]
    med = float(np.median(seg))
    mad = float(np.median(np.abs(seg - med)))
    sigma = 1.4826 * mad + EPS
    return (value - med) / sigma


def log_returns(closes: npt.ArrayLike) -> FloatArray:
    c = _as_float64(closes)
    if len(c) < 2:
        return np.array([], dtype=np.float64)
    return np.diff(np.log(np.maximum(c, EPS)))


def lag1_autocorr(arr: npt.ArrayLike) -> float:
    """Pearson lag-1 autocorrelation; returns 0 if undefined."""
    a = _as_float64(arr)
    if len(a) < 3:
        return 0.0
    a0 = a[:-1]
    a1 = a[1:]
    m0 = a0.mean()
    m1 = a1.mean()
    s0 = a0.std()
    s1 = a1.std()
    if s0 <= EPS or s1 <= EPS:
        return 0.0
    cov = float(np.mean((a0 - m0) * (a1 - m1)))
    return cov / float(s0 * s1)


def sigmoid(x: float, *, gain: float = 1.0) -> float:
    """Numerically stable sigmoid bounded to (0,1)."""
    if x >= 0:
        z = math.exp(-gain * x)
        return 1.0 / (1.0 + z)
    z = math.exp(gain * x)
    return z / (1.0 + z)


def clip01(x: float) -> float:
    if math.isnan(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def percentile_rank(value: float, history: npt.ArrayLike) -> float:
    """Empirical CDF rank of `value` inside `history`, in [0,1]."""
    h = _as_float64(history)
    if len(h) == 0:
        return 0.5
    rank = float((h <= value).sum())
    return rank / len(h)


def wick_pressure_from_ohlc(open_: float, high: float, low: float, close: float) -> float:
    body = abs(close - open_)
    upper = high - max(open_, close)
    lower = min(open_, close) - low
    return (upper + lower) / max(body, 1e-9)


def momentum_sign_flipped(closes: npt.ArrayLike) -> bool:
    c = _as_float64(closes)
    if len(c) < 3:
        return False
    m_prev = float(np.sign(c[-2] - c[-3]))
    m_curr = float(np.sign(c[-1] - c[-2]))
    if m_prev == 0.0 or m_curr == 0.0:
        return False
    return m_prev != m_curr
