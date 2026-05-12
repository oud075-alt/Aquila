# ADR-0001 — Structural State Precedence

Status: Accepted
Date: 2026-05-11

## Context

Appendix U defines seven structural states with conditions that can
overlap. For example, a bar may simultaneously satisfy `UP_CONTINUATION`
(close>open ∧ DE>0.6 ∧ slope>0) and `VOLATILITY_EXPANSION`
(rolling_range/ATR_64 > 1.5).

Appendix U does not specify precedence. The state classifier must be
deterministic and single-valued per bar.

## Decision

Apply states in the following priority order; the first match wins:

```
1. REVERSAL_PRESSURE
2. LIQUIDITY_STALL
3. VOLATILITY_EXPANSION
4. COMPRESSION
5. UP_CONTINUATION
6. DOWN_CONTINUATION
7. CHAOTIC_TRANSITION   (default fallback)
```

## Justification

- Pathology-bearing states (`REVERSAL_PRESSURE`, `LIQUIDITY_STALL`,
  `VOLATILITY_EXPANSION`) carry stronger structural signal than
  directional states; they describe *disorder*, which is the system's
  raison d'être.
- `COMPRESSION` ranks above directional continuation because compression
  invalidates the premise of "healthy continuation" — a small-range bar
  inside an apparent trend is structurally a compression artifact.
- `CHAOTIC_TRANSITION` is the fallback for bars that satisfy no rule,
  per Appendix U's explicit "default fallback state ONLY" clause.

## Consequences

- The state alphabet is single-valued and deterministic.
- Modules that need to query "is this also an UP_CONTINUATION?" must use
  the multi-condition booleans directly rather than the chosen label.
- Phase 5 learning may not change this precedence.
