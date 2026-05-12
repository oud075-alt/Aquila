# ADR-0004 — Pathology Aggregation Rule

Status: Accepted
Date: 2026-05-11

## Context

Appendix M defines six pathology primitives each ∈ [0,1]. The
`PathologyScores.aggregate` field is required but its formula is not
explicitly specified.

Appendix O specifies geometric mean for *confidence aggregation*, but
confidence and pathology compose oppositely (confidence multiplies
"goodness", pathology accumulates "badness"). Geometric mean of pathology
scores would under-weight a single severe primitive.

## Decision

Pathology aggregation uses a **noisy-OR** combination of the six
primitives with uniform weights:

```
aggregate = 1 - Π_i (1 - p_i)^(w_i)        with Σ w_i = 1, w_i = 1/6
```

Equivalently:

```
aggregate = 1 - exp( (1/6) * Σ_i log(1 - p_i + ε) )
```

`structural_health = 1 - aggregate`.

`instability_score = max(entropy_instability, volatility_disorder,
dispersion_shock, continuation_decay)` — the worst structural driver.

`escalation_risk = clip01(0.5 * aggregate + 0.5 * slope(aggregate, 16))`
where `slope` is the OLS slope over the last 16 aggregate values, scaled
into [0,1] via tanh-derived bounded mapping.

## Justification

- Noisy-OR is the standard rule for combining independent failure
  signals: any one severe primitive pushes the aggregate toward 1, while
  multiple moderate primitives still combine intuitively.
- It is symmetric (treating all six primitives identically), bounded
  [0,1], smooth, and differentiable — required by future Phase 5
  Bayesian calibration.
- `instability_score` as the max-of-disorder primitives surfaces the
  *worst structural disorder* without averaging it away.
- `escalation_risk` mixes level and trend so a rapidly worsening but
  still-moderate aggregate still triggers defensive postures.

## Consequences

- The orchestrator and contradiction validator can rely on
  `instability_score` being a proper bound (∈ [0,1]) of structural
  disorder.
- Phase 5 may recalibrate the noisy-OR weights using deterministic
  Bayesian updating only.
