# ADR-0003 — INVALID Contradiction Policy Behavior

Status: Accepted
Date: 2026-05-11

## Context

Appendix X defines three actions for the INVALID policy:

- reject diagnosis
- return validation failure
- reduce confidence to 0

Appendix G mandates that *catastrophic pipeline failure is not allowed*
and that *partial diagnosis is allowed with degraded confidence*.

A literal "reject diagnosis" that drops the diagnosis altogether
contradicts Appendix G.

## Decision

The INVALID policy is implemented as a **soft-reject with validation
flag**, not a hard drop:

1. The `DiagnosisEnvelope` is still emitted to downstream consumers.
2. `confidence` is set to `0.0`.
3. `validation_failed` is set to `True`.
4. `defensive_state` is forced to `True`.
5. The triggering contradiction pair is recorded in
   `reasoning.invalid_pairs`.
6. The orchestrator increments the `contradictions.invalid_total`
   metric and emits a `WARN` log with the offending pair.

UNSTABLE and CRITICAL policies behave as their plain-language semantics:

- UNSTABLE: `confidence *= 0.5`; `contradiction_score = max(score, 0.7)`.
- CRITICAL: `defensive_state = True`; `escalation_risk = max(risk, 0.85)`;
  `participation_safety = min(safety, 0.15)`.

## Justification

- Preserves Appendix G's *no catastrophic failure* guarantee.
- Still satisfies Appendix X's INVALID semantics (the diagnosis is
  effectively unusable: confidence zero, defensive forced, flagged).
- Maintains observability — analysts can inspect *why* INVALID fired.
- Composable with the API: `/diagnosis` always returns a 200 with a
  valid envelope; failures are signalled in payload, not by HTTP error.

## Consequences

- API consumers must check `validation_failed` and `confidence > 0`
  before treating a diagnosis as actionable structural intelligence.
- CI behavior boundary test (Appendix P) verifies that an INVALID
  diagnosis still does not contain any forbidden field.
