# ADR-0006 — Rename `BayesianReasoner` → `HeuristicScoreFuser`

## Status
Accepted (M3.1).

## Context
The class formerly known as `BayesianReasoner` lives in
`aquila/probabilistic/bayes.py`. The module docstring claimed
"Bayesian-flavored confidence propagation". A reader who knew Bayesian
inference would expect:

- explicit likelihood functions per hypothesis, e.g. `P(E|H)` and `P(E|¬H)`;
- a normalisation step so posteriors over competing hypotheses sum to 1;
- log-likelihood accumulation or some equivalent of `posterior ∝ prior × likelihood`;
- a coherent treatment of independent vs. correlated evidence.

The actual implementation did none of those things. Its body, in full,
was:

```python
agg = ConfidenceCalculus.weighted_mean([(e.weight, e.likelihood) for e in evidence])
posterior = ConfidenceCalculus.weighted_mean([(1.0, prior), (sum(e.weight for e in evidence), agg)])
```

This is a two-stage weighted mean: average the evidence "likelihoods"
weighted by their own weights, then average the prior against that
aggregate weighted by the evidence weight sum. There is no likelihood
ratio. There is no normalisation over hypotheses. There is no
posterior in the Bayesian sense.

The name was therefore a name-trap: a developer adding new features to
"the Bayesian module" would write code that assumed Bayesian semantics
and silently violate them.

## Decision
Rename `BayesianReasoner` → `HeuristicScoreFuser`. Method `.update()`
is renamed `.fuse()` (with `.update()` retained as a method alias for
backward compatibility in this PR cycle).

This is option 1 of the rename-vs-rewrite choice posed by the master
roadmap. Option 2 — actually implementing Bayesian updates — is
deferred. It would require declaring the hypothesis space, the
likelihood functions per hypothesis, and a normalisation policy. None
of these are specified anywhere in the codebase today, so writing the
Bayes code now would be writing speculation. Rename is the honest move.

### What the old name claimed
- Bayesian posterior calculation.
- A formal probability model.
- Compatibility with downstream code that expects posteriors to behave like probabilities under hypothesis competition.

### What the code actually does
- Weighted-mean fusion of arbitrary likelihood-shaped scalars.
- Clipping the result to `[0, 1]` via `safe_prob`.
- No competition between hypotheses; each call handles one hypothesis name in isolation.

### Why the new name fits
`HeuristicScoreFuser` says exactly what the code does: it is a
heuristic; it fuses scores; it does not compute posteriors.

## Migration plan (per HARD RULE #8)

1. **This PR (M3.1)**: introduce `HeuristicScoreFuser`. Keep `BayesianReasoner` as a subclass alias whose metaclass emits `DeprecationWarning` on every attribute access. Update repo-internal call sites to the new name. Add this ADR.
2. **Two PRs later**: drop the `BayesianReasoner` alias and the `.update()` method alias.

## Consequences
- The import `from aquila.probabilistic import BayesianReasoner` still works in this PR cycle.
- Any caller will see a `DeprecationWarning`.
- Tests now use `HeuristicScoreFuser.fuse(...)`.
- `aquila/core/confidence.py` docstring is updated to remove "Bayesian-flavoured" so we don't reintroduce the same trap one directory away.

## Non-decisions
- We do **not** delete the legacy alias in this PR.
- We do **not** add new functionality.
- We do **not** rename the module file `bayes.py` — module file renames are a separate concern (would change the import path) and should be batched after the alias is dropped.

## References
- `aquila/probabilistic/bayes.py` — the renamed class.
- `aquila/probabilistic/__init__.py` — re-exports.
- `tests/test_subsystems.py::test_heuristic_score_fuser_fuses` — replaces the old `test_bayesian_reasoner_updates`.
- HARD RULE #2 (no overclaim vocabulary) and HARD RULE #8 (deprecation alias for 2 PRs) in the master roadmap.
