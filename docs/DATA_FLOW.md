# Data Flow & Event Lifecycle

## Per-tick data flow

```
RawEvent (Layer 0)
   │
   ▼  normalize + dedup + origin tag
PrimitiveBar
   │
   ▼  L1.process(bar, ctx)
LayerOutput[PrimitiveSnapshot]
   │
   ├──► EventBus.publish ──► AuditLog.append (hash chain) ──► EventStore.append
   │
   ▼  L2.process(snapshot, ctx)
LayerOutput[StructuralDiagnosis]
   │
   ├──► EventBus / Audit / EventStore
   │
   ▼  L3.process(diagnosis, ctx)
LayerOutput[PathologyReport]
   │
   ▼ fan-out
   ├──► L4 EpisodicMemoryLayer ─► LayerOutput[MemoryRecall]
   ├──► L5 TemporalHierarchyLayer ─► LayerOutput[TemporalCognition]
   ├──► L6 DeceptionIntelligenceLayer ─► LayerOutput[DeceptionReport]
   └──► L7 RegimeMutationLayer ─► LayerOutput[RegimeMutationReport]
   │
   ▼  L8.process({}, ctx)  -- reads all upstream from ctx
LayerOutput[MetaCognitiveReport]   +   MetaSignal (carried into next cycle)
```

## Event lifecycle phases

```
INGEST → PRIMITIVES → STRUCTURAL → PATHOLOGY → [MEMORY|TEMPORAL|DECEPTION|REGIME] → META → AUDIT → DONE
```

Each phase emits a `LayerOutput` that is:
1. Validated by `SafetyKernel.enforce` (raises on forbidden fields).
2. Published on the in-process `EventBus`.
3. Appended to `AuditLog` with `prev_hash` linkage.
4. (When `AppState.record` is called from API) appended to the `EventStore` projections.

## Failure / degraded path

If any layer raises during `process`, the orchestrator captures the error
into a synthetic `LayerOutput` with `visibility="degraded"` and
`error_state=str(exc)`. Downstream layers see this as a degraded input;
L8 detects ≥ 2 degraded outputs and raises `FailureState`.

## Replay path

```
RawEvent[] → ReplayScheduler.schedule (sort by ts)
           → ReplayClock seeded at events[0].timestamp
           → CognitiveOrchestrator (memory=write_on_real=False)
           → emits LayerOutput[*] with origin="replay"
           → no real-archive writes
```
