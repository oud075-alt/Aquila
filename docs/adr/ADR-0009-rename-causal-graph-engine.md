# ADR-0009 — Rename `CausalGraphEngine` → `LineageGraph`

## Status
Accepted (M3.2).

## Context
`CausalGraphEngine` lives in `aquila/causal/engine.py`. Its module
docstring read "Builds an event-level causal graph for a single cycle.
... no learned causality." Its body, in full, does two things:

1. Walks a hand-written tuple of `(LayerName, LayerName, CausalEdgeKind)`
   adjacencies (the pipeline DAG) and emits one edge per matched pair
   of layer outputs in the current cycle.
2. For every layer output, walks its `evidence: list[EventRef]` list
   and emits one edge per citation.

That is not causal inference. There is no intervention, no
counterfactual reasoning, no do-calculus, no learned graph structure,
no test of independence. The edges are entirely a function of two
inputs: the static pipeline shape and the explicit evidence citations
attached upstream. The honest description is **lineage**: which
upstream output was cited by which downstream output, in this single
cycle.

The name "causal" was a name-trap. A developer reading
`CausalGraphEngine().build(outputs)` would, reasonably, expect that
edges represented some empirical causal claim and would write
downstream code (e.g. attribution, intervention simulators) on that
assumption. The class never met that contract.

## Decision
Rename `CausalGraphEngine` → `LineageGraph`. Keep `CausalGraphEngine`
as a subclass alias whose metaclass emits `DeprecationWarning` on every
attribute access (HARD RULE #8). Update all internal call sites to the
new name. The schema classes `CausalEdge`, `CausalEdgeKind`,
`CausalGraph` are NOT renamed in this PR because they cross the wire
(FastAPI routes, JSON-LD export) and renaming them would require a
schema-version bump that does not belong in a single-rename PR.

### What the old name claimed
- Causal inference.
- An empirically-meaningful directed graph.
- Compatibility with downstream code that expects causal semantics
  (intervention, attribution, counterfactuals).

### What the code actually does
- Reads a hard-coded pipeline DAG and emits one edge per pipeline-edge
  whose endpoints are both present in the current cycle.
- Reads every layer output's explicit evidence list and emits one edge
  per citation.

### Why the new name fits
`LineageGraph` says exactly what the code does. The output records
event lineage — which event_id was cited by which other event_id —
within one cycle. This is a useful, transparent, deterministic
artefact. It just isn't causality.

## Migration plan (per HARD RULE #8)

1. **This PR (M3.2)**: introduce `LineageGraph`. Keep `CausalGraphEngine`
   as a subclass alias with `DeprecationWarning` on access. Update all
   in-repo call sites (`aquila/query/engine.py`, tests). Add this ADR.
2. **Two PRs later**: drop the `CausalGraphEngine` alias.

The schema rename (`CausalEdge` etc.) is a separate concern, scheduled
for a later PR that also handles the schema-version bump and the
FastAPI route / JSON-LD export updates.

## Consequences
- `from aquila.causal import CausalGraphEngine` still works in this PR
  cycle. Any caller will see a `DeprecationWarning`.
- `from aquila.causal import LineageGraph` is the new canonical import.
- `aquila/query/engine.py` already uses the new name.
- `tests/test_subsystems.py::test_lineage_graph_builds_for_pipeline_outputs`
  replaces the old `test_causal_graph_builds_for_pipeline_outputs`.
- ADR-0005's no-overclaim policy named "Causal" as a reserved word. The
  rename brings the engine class into compliance. The schema names are
  acknowledged exceptions until the wire schema is bumped.

## Non-decisions
- We do **not** rename the schema types in this PR.
- We do **not** rename the module path `aquila/causal/`.
- We do **not** delete the legacy alias in this PR.

## References
- `aquila/causal/engine.py` — the renamed class.
- `aquila/causal/__init__.py` — re-exports.
- `aquila/query/engine.py` — internal caller updated.
- `tests/test_rename_lineage_graph.py` — rename contract tests.
- ADR-0005 — overclaim policy that named "Causal" as a reserved word.
- ADR-0006 — sibling rename (BayesianReasoner → HeuristicScoreFuser) using the same pattern.
