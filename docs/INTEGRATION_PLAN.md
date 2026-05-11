# Integration Plan with Current MSPIS

## Premise

The prompt declares the following as **already existing**:

- FastAPI backend
- Structural diagnosis
- Pathology analysis
- Contradiction engine
- Confidence scoring
- Replay framework
- Primitive metrics
- Market state abstraction

In this repository they were absent. To preserve the *contract* of the
prompt — "do NOT rewrite, do NOT simplify, do NOT collapse" — this build:

1. Provides **L1 / L2 / L3** as minimum-surface stubs preserving the
   documented public types (`PrimitiveSnapshot`, `StructuralDiagnosis`,
   `PathologyReport`, plus `ContradictionEngine` accessed via
   `pathology.contradiction.detect_contradictions`).
2. Defines `CognitiveLayer` as the **only** stable contract the new layers
   depend on. Any production MSPIS implementation of L1–L3 that exposes
   `CognitiveLayer[InputModel, OutputModel].process(payload, ctx)` is
   drop-in compatible.

## Drop-in integration steps for an existing MSPIS deployment

1. **Adapter shim** — wrap each existing MSPIS class with a `CognitiveLayer`
   adapter that delegates `process()` to the existing entrypoint.
2. **Schema adoption** — replace stub Pydantic schemas in
   `aquila/primitives/schemas.py`, `aquila/structural/schemas.py`,
   `aquila/pathology/schemas.py` with the production MSPIS schemas. Pin
   their `schema_version` in `aquila.protocols.compatibility`.
3. **Replay framework alignment** — if MSPIS already has a replay runner,
   register an `EventTransport` adapter so its events are visible to
   Aquila's `EventBus`. The reverse path (Aquila → MSPIS) is also valid.
4. **Confidence aggregation** — pipeline L4–L8 will work with any L3 that
   emits a `PathologyReport` containing `aggregate_pathology_score` and
   `aggregate_contradiction_score`. If the MSPIS version names those
   differently, extend `confidence.py` with a mapping function.
5. **Safety Kernel** — wrap every existing MSPIS layer output emission
   with `SafetyKernel.enforce` before publishing. This is a pure addition
   and does not alter MSPIS semantics.
6. **Audit log** — point the existing MSPIS audit writer at
   `observability.audit.AuditLog.append`. The hash-chain feature is
   additive and tamper-evident.

## Backward-compat strategy

- **Schema versioning**: every output carries `schema_version`. A vNext
  payload remains decodable by older consumers because Pydantic models
  ignore unknown fields by default unless `extra="forbid"` is set
  (it is *not* set on layer payload schemas).
- **Ontology versioning**: `OntologyRegistry.publish` appends a new
  snapshot; old replays still validate against their captured snapshot.
- **Protocol negotiation**: `ProtocolCompatibilityMatrix.is_compatible`
  checks major versions only. Minor / patch versions are forward-compatible.

## Non-disruption guarantees

- No existing MSPIS module is touched at runtime.
- No new layer creates implicit dependencies upward into L1–L3.
- All new layers are opt-in: instantiating `CognitiveOrchestrator` is
  what activates them; MSPIS can continue running its existing pipeline
  in parallel and selectively forward outputs to the new layers.
