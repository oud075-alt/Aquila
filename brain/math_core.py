"""Numerical primitives shared across pathology / expectation modules.

Every statistical quantity used by MSPIS is implemented here so that the
analytical modules stay focused on diagnosis logic, not arithmetic. All
functions are pure, NumPy-backed, NaN-safe and deterministic.
"""

from __future__ import annotations

from typing import Sequence, Tuple

import math
import numpy as np


# ---------------------------------------------------------------------------
# Safe array helpers
# ---------------------------------------------------------------------------
def as_array(x: Sequence[float] | np.ndarray) -> np.ndarray:
    """Convert *x* to a 1-D float64 array, dropping NaN/Inf."""
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1)
    return a


def safe_array(x: Sequence[float] | np.ndarray, fill: float = 0.0) -> np.ndarray:
    a = as_array(x).copy()
    bad = ~np.isfinite(a)
    if bad.any():
        a[bad] = fill
    return a


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if not np.isfinite(value):
        return lo
    return float(min(hi, max(lo, value)))


def safe_div(num: float, den: float, default: float = 0.0) -> float:
    if not np.isfinite(num) or not np.isfinite(den) or abs(den) < 1e-12:
        return default
    return float(num / den)


# ---------------------------------------------------------------------------
# Logistic & probability transforms
# ---------------------------------------------------------------------------
def logistic(x: float, k: float = 1.0, x0: float = 0.0) -> float:
    """Numerically safe logistic mapping ``ℝ → (0,1)``."""
    try:
        return float(1.0 / (1.0 + math.exp(-k * (x - x0))))
    except OverflowError:
        return 0.0 if (x - x0) < 0 else 1.0


def abs_logistic(x: float, k: float = 1.0) -> float:
    """Map ``|x|`` through a logistic centred at zero, returns [0,1]."""
    return logistic(abs(float(x)), k=k, x0=0.0) * 2.0 - 1.0 if False else logistic(
        abs(float(x)), k=k, x0=0.0
    ) * 2.0 - 1.0


def probability_or(probs: Sequence[float]) -> float:
    """Independent-event probability fusion: ``1 - Π(1 - p_i)``."""
    p = 1.0
    for v in probs:
        v = clamp(float(v), 0.0, 1.0)
        p *= (1.0 - v)
    return clamp(1.0 - p, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Statistical estimators
# ---------------------------------------------------------------------------
def robust_zscore(x: np.ndarray, value: float) -> float:
    """Modified z-score using median & MAD (robust to outliers)."""
    x = safe_array(x)
    if x.size < 5:
        return 0.0
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) or 1e-9
    return float(0.6745 * (value - med) / mad)


def rolling_std(x: np.ndarray, window: int) -> np.ndarray:
    x = safe_array(x)
    if x.size == 0:
        return x
    window = max(2, min(window, x.size))
    out = np.zeros_like(x)
    for i in range(x.size):
        a = x[max(0, i - window + 1) : i + 1]
        out[i] = float(np.std(a, ddof=1)) if a.size > 1 else 0.0
    return out


def realized_volatility(returns: np.ndarray, annualize: bool = False, bars_per_year: int = 365 * 24) -> float:
    r = safe_array(returns)
    if r.size < 2:
        return 0.0
    s = float(np.std(r, ddof=1))
    return s * math.sqrt(bars_per_year) if annualize else s


def ewma(x: np.ndarray, span: int) -> np.ndarray:
    """Exponentially weighted moving average."""
    x = safe_array(x)
    if x.size == 0:
        return x
    alpha = 2.0 / (span + 1.0)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, x.size):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def linear_regression(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """OLS slope, intercept and R²."""
    x = safe_array(x)
    y = safe_array(y)
    n = min(x.size, y.size)
    if n < 3:
        return 0.0, 0.0, 0.0
    x = x[-n:]
    y = y[-n:]
    xm = float(np.mean(x))
    ym = float(np.mean(y))
    cov = float(np.mean((x - xm) * (y - ym)))
    varx = float(np.var(x)) or 1e-12
    slope = cov / varx
    intercept = ym - slope * xm
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - ym) ** 2)) or 1e-12
    r2 = 1.0 - ss_res / ss_tot
    return slope, intercept, clamp(r2, 0.0, 1.0)


def autocorrelation(x: np.ndarray, lag: int = 1) -> float:
    x = safe_array(x)
    if x.size <= lag + 2:
        return 0.0
    a = x[:-lag] - np.mean(x[:-lag])
    b = x[lag:] - np.mean(x[lag:])
    denom = float(np.sqrt(np.sum(a * a) * np.sum(b * b))) or 1e-12
    return clamp(float(np.sum(a * b) / denom), -1.0, 1.0)


def hurst_exponent(x: np.ndarray, max_lag: int = 50) -> float:
    """Generalised Hurst exponent estimator (returns value in roughly [0,1])."""
    x = safe_array(x)
    if x.size < max_lag * 2:
        max_lag = max(5, x.size // 4)
    if max_lag < 5:
        return 0.5
    lags = range(2, max_lag)
    tau = []
    for lag in lags:
        diff = x[lag:] - x[:-lag]
        if diff.size < 2:
            tau.append(1e-9)
            continue
        tau.append(np.std(diff) + 1e-12)
    log_lags = np.log(list(lags))
    log_tau = np.log(tau)
    slope, _, _ = linear_regression(log_lags, log_tau)
    return clamp(slope, 0.0, 1.0)


def shannon_entropy(samples: np.ndarray, bins: int = 16) -> float:
    """Normalised Shannon entropy of a 1-D distribution (range [0,1])."""
    x = safe_array(samples)
    if x.size < 5:
        return 0.0
    hist, _ = np.histogram(x, bins=bins, density=False)
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return 0.0
    p = hist / total
    p = p[p > 0]
    H = -float(np.sum(p * np.log(p)))
    return clamp(H / math.log(bins), 0.0, 1.0)


def directional_coherence(returns: np.ndarray) -> float:
    """Measure of how consistent the sign of returns is. Range [0,1]."""
    r = safe_array(returns)
    if r.size < 2:
        return 0.0
    s = np.sign(r)
    same = float(np.mean(s[1:] == s[:-1]))
    return clamp(same, 0.0, 1.0)


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    high = safe_array(high)
    low = safe_array(low)
    close = safe_array(close)
    prev_close = np.concatenate(([close[0]], close[:-1])) if close.size else close
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    return np.maximum.reduce([tr1, tr2, tr3])


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    tr = true_range(high, low, close)
    if tr.size == 0:
        return tr
    return ewma(tr, span=period)


def bollinger_width(close: np.ndarray, period: int = 20, k: float = 2.0) -> np.ndarray:
    close = safe_array(close)
    n = close.size
    if n == 0:
        return close
    out = np.zeros(n)
    for i in range(n):
        a = close[max(0, i - period + 1) : i + 1]
        if a.size < 2:
            continue
        m = float(np.mean(a))
        s = float(np.std(a, ddof=1))
        upper = m + k * s
        lower = m - k * s
        out[i] = (upper - lower) / (m if abs(m) > 1e-12 else 1e-12)
    return out


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    close = safe_array(close)
    if close.size < period + 1:
        return np.full(close.size, 50.0)
    delta = np.diff(close, prepend=close[0])
    up = np.where(delta > 0, delta, 0.0)
    dn = np.where(delta < 0, -delta, 0.0)
    roll_up = ewma(up, span=period)
    roll_dn = ewma(dn, span=period)
    rs = roll_up / np.where(roll_dn == 0, 1e-12, roll_dn)
    return 100.0 - 100.0 / (1.0 + rs)


def momentum(close: np.ndarray, period: int = 10) -> np.ndarray:
    close = safe_array(close)
    if close.size <= period:
        return np.zeros_like(close)
    out = np.zeros_like(close)
    out[period:] = close[period:] - close[:-period]
    return out


def trend_efficiency(close: np.ndarray, period: int = 20) -> float:
    """Kaufman efficiency ratio in [0,1]."""
    close = safe_array(close)
    if close.size < period + 1:
        return 0.0
    change = abs(close[-1] - close[-period - 1])
    path = float(np.sum(np.abs(np.diff(close[-period - 1 :]))))
    return clamp(safe_div(change, path), 0.0, 1.0)


def slope_normalized(close: np.ndarray, period: int = 30) -> float:
    """Regression slope expressed as relative move per bar."""
    close = safe_array(close)
    if close.size < period + 2:
        return 0.0
    y = close[-period:]
    x = np.arange(y.size, dtype=np.float64)
    slope, _, _ = linear_regression(x, y)
    base = max(abs(float(np.mean(y))), 1e-12)
    return float(slope / base)
