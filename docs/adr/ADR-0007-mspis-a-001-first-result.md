# ADR-0007 — MSPIS-A-001 v0.1.0 — first empirical run

## Status
Accepted (M1.5). Result: **success_metric NOT passed**, but lift positive and significant.

## Context
PR M1.3 registered `MSPIS-A-001` v0.1.0 with the declared success metric
`precision >= 0.55`, baseline `random_bar_sampler`, significance
`bootstrap_p < 0.05`. PR M1.4 introduced the walk-forward backtest
harness. This ADR records the first empirical run, executed against the
committed synthetic fixture `tests/data/synthetic_bars_seed42.jsonl`
(2000 bars, two 500-bar volatility regimes, seed = 42).

Command used (exactly):

```bash
python -m aquila.experiments.backtest \
    --detector MSPIS-A-001 \
    --data tests/data/synthetic_bars_seed42.jsonl \
    --symbol SYN42 \
    --train-window 250 \
    --seed 1337 \
    --out docs/empirical/MSPIS-A-001-v0.1.0.json \
    --out-jsonld docs/empirical/MSPIS-A-001-v0.1.0.jsonld
```

Report committed at `docs/empirical/MSPIS-A-001-v0.1.0.json` and
`docs/empirical/MSPIS-A-001-v0.1.0.jsonld`.

## Result (verbatim from the report)

| Field | Value |
|-------|-------|
| `n_events` | 2000 |
| `n_triggers_detector` | 98 |
| `n_triggers_baseline` | 91 |
| `precision_detector` | 0.5154639175257731 |
| `precision_baseline` | 0.23076923076923078 |
| `lift` (detector − baseline) | 0.28469468675654236 |
| `bootstrap_p_value` (B = 1000, paired) | 0.0 |
| `bootstrap_ci_95` (mean-diff) | [0.14931460292285037, 0.4118046901552056] |
| `success_metric_passed` | **false** |

## Decision

The detector **did not pass** its declared success metric (`precision >=
0.55`). It did, however, beat the random baseline by 0.28 absolute
precision with a bootstrap p-value below 0.001 and a 95% CI that does
not include zero. We do **not** rename, reclaim, or relax the threshold
to make it pass.

### What this run does prove
- The harness end-to-end runs deterministically on a committed fixture.
- On this synthetic distribution, the detector's success rate is
  significantly higher than a rate-matched random baseline.
- The lookahead guard in `OutcomeEnricher` and the strict-after
  trigger-timestamp convention (`bar.timestamp + 1µs`) did not raise.

### What this run does NOT prove
- The detector works on real market data. The fixture is a Gaussian
  random walk with a regime switch — there is no microstructure, no
  spread, no order flow, no real news shock.
- Generalisation across symbols. Only one synthetic symbol was tested.
- The `success_expression` `abs(realized_return) <= 0.5 * range_at_trigger`
  is the right success criterion. It was chosen up-front; if it is
  wrong, the detector can pass for the wrong reason. M2.3 will sweep
  multiple symbol profiles to probe this.

## Consequences
1. The detector remains in `SCAFFOLDED` status. No status upgrade to
   `VERIFIED_EMPIRICAL` is made by this PR.
2. The next step in the roadmap (M2 — `CalibrationStore`) is required
   to remove the hard-coded rolling threshold and the hard-coded
   `volume_z <= -0.3`. Re-running the backtest under calibrated
   thresholds is M2.2; cross-symbol replication is M2.3.
3. Per the master roadmap, all milestones except M2 and M3 are now
   paused pending a decision review of this result.

## Deviations from the roadmap text
- The roadmap requested a `.parquet` fixture; this ADR ships a `.jsonl`
  fixture because the M1.4 loader supports `.jsonl` only and parquet
  support is explicitly deferred until M4. Switching the suffix is a
  trivial change once `pyarrow` is added as a dependency.

## References
- `tests/data/generate_synthetic_seed42.py` — fixture generator (regenerates byte-for-byte from seed 42).
- `tests/data/synthetic_bars_seed42.jsonl` — committed fixture.
- `docs/empirical/MSPIS-A-001-v0.1.0.json` — full report.
- `docs/empirical/MSPIS-A-001-v0.1.0.jsonld` — JSON-LD wrapper.
- `aquila/detectors/builtin/mspis_a_001.py` — detector definition.
