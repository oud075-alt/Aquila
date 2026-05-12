# ADR-0002 — Window & Metric Definitions

Status: Accepted
Date: 2026-05-11

## Context

Appendix U references several metrics whose computation is not pinned:
`rolling_range`, `trend_slope`, `directional_efficiency`, `volume_zscore`,
`range_zscore`, `wick_pressure`, `momentum_sign flipped`, `ATR_64`.

## Decision

Canonical definitions, used by **every** module consuming these names:

### ATR_64

Wilder's ATR with period 64.

```
TR_t = max(high_t - low_t,
           |high_t - close_{t-1}|,
           |low_t  - close_{t-1}|)
ATR_64_t = Wilder_smoothing(TR, period=64)
```

### rolling_range

Per-bar range of the current bar:

```
rolling_range_t = high_t - low_t
```

(For multi-bar use sites, this is explicitly named `range_window_N`.)

### trend_slope

OLS slope of `close` over the last 32 bars, normalized by the mean
close to make it scale-invariant:

```
trend_slope_t = OLS_slope(close[t-31 : t+1]) / mean(close[t-31 : t+1])
```

### directional_efficiency (Kaufman efficiency ratio over 32 bars)

```
directional_efficiency_t =
    |close_t - close_{t-31}|
    /
    Σ_{i=t-30..t} |close_i - close_{i-1}|
```

Bounded to [0.0, 1.0]; values near 1 = pure directional move,
values near 0 = noisy / non-directional.

### volume_zscore / range_zscore

Robust z-score over a rolling window of 64 bars using median and MAD:

```
robust_z(x, window=64) =
    (x - median(window)) / (1.4826 * MAD(window) + 1e-12)
```

### wick_pressure

Sum of upper and lower wicks, expressed in candle-body units:

```
body_t        = |close_t - open_t|
upper_wick_t  = high_t - max(open_t, close_t)
lower_wick_t  = min(open_t, close_t) - low_t
wick_pressure_t = (upper_wick_t + lower_wick_t) / max(body_t, 1e-9)
```

### momentum_sign flipped

Defined relative to the previous one-bar momentum direction:

```
m_t      = sign(close_t - close_{t-1})
flipped  = (m_t != 0) AND (m_{t-1} != 0) AND (m_t != m_{t-1})
```

Zero-momentum bars do not count as flips.

## Justification

- Kaufman's efficiency ratio is the standard definition of "directional
  efficiency" in market microstructure.
- Robust z-score (median/MAD) is preferred over mean/std because Phase 0
  must remain stable under heavy-tailed return distributions.
- Wilder's ATR is the canonical 64-period ATR.
- Normalizing slope by mean close prevents price-magnitude drift across
  long replays (BTC moves from 30k → 100k must not change slope semantics).

## Consequences

- All six pathology primitives and the state classifier consume these
  exact definitions through `core/pathology/metrics.py`.
- Phase 1+ modules must not recompute these primitives ad hoc.
