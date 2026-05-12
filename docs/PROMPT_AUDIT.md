# Prompt Audit — Gaps, Closures, Scope Statement

This is the audit of the Aquila/MSPIS architectural prompt. It has been
expanded twice; this document captures the union of gaps and how the build
closes them, plus an honest scope statement.

---

## Honest scope statement

The expanded prompt now specifies ~8 cognitive layers + ~25 supporting
subsystems (causal graph, ontology, ingestion, simulation, validation, etc.).
This is a multi-subsystem research platform.

What this PR delivers:

| Element | State |
|---------|-------|
| Cognitive Layers L1–L8 | **IMPLEMENTED** (functional, tested) |
| Cognitive pipeline orchestrator + event bus | **IMPLEMENTED** |
| Safety kernel (no-signal enforcement) | **IMPLEMENTED** |
| Episodic Memory store (in-mem + JSONL) | **IMPLEMENTED** |
| Replay framework (deterministic, slice-aware) | **IMPLEMENTED** |
| FastAPI surface for all layers | **IMPLEMENTED** |
| Ingestion (adapter interface + in-proc adapter) | **IMPLEMENTED** |
| Narrative / explainability emitter | **IMPLEMENTED** |
| Causal graph engine | **SCAFFOLDED** (typed interfaces + minimal implementation) |
| Liquidity ontology | **SCAFFOLDED** |
| Transition physics engine | **SCAFFOLDED** |
| Cross-asset intermarket cognition | **SCAFFOLDED** |
| Data governance + event sourcing log | **SCAFFOLDED** |
| Structural simulation / counterfactual | **SCAFFOLDED** |
| Drift monitor | **SCAFFOLDED** |
| Ontology registry + versioning | **SCAFFOLDED** |
| Cognitive query interface | **SCAFFOLDED** |
| Heuristic score fusion (formerly "Probabilistic Bayesian framework"; renamed in M3.1) | **SCAFFOLDED** |
| Attention allocator | **SCAFFOLDED** |
| Research experiment harness | **SPECIFIED** (doc + folder) |
| Distributed runtime / IPC transport | **SPECIFIED** |
| Real-time ingestion gateways (Kafka/NATS) | **SPECIFIED** |
| Scientific validation framework | **SCAFFOLDED** (suite skeleton) |
| Observability (logging + audit) | **IMPLEMENTED** |

Everything marked **SCAFFOLDED** ships with typed interfaces, Pydantic
schemas, and a minimal in-process implementation that returns valid empty
results — no `NotImplementedError`, so the system runs end-to-end. Items
marked **SPECIFIED** are documented in `docs/` and have folder + `__init__.py`
ready for future implementation.

---

## Gap closure table

### Pass 1 (original prompt)

| # | Gap | Closure |
|---|-----|---------|
| 1 | Header says 7 layers, body lists 8 | Build all 8 |
| 2 | No Layer 0 — Data Ingestion | `aquila/ingestion/` |
| 3 | No Narrative output layer | `aquila/narrative/` |
| 4 | No centralized Safety Kernel | `aquila/safety/` |
| 5 | No persistence strategy | `MemoryStore` interface + impls |
| 6 | No event bus | `aquila/pipeline/event_bus.py` |
| 7 | No determinism contract | `ReplayContext` w/ frozen clock + seed |
| 8 | No observability | `aquila/observability/` |
| 9 | No configuration model | `aquila/config/` |
| 10 | No confidence propagation formalism | `core/confidence.py` (ConfidenceCalculus) |
| 11 | No timeframe semantics | `core/time.py` |
| 12 | No failure / backpressure model | `LayerOutput.error_state`, degraded visibility |
| 13 | No schema versioning | `schema_version` on every output |
| 14 | No multi-symbol abstraction | `Symbol` carried throughout |
| 15 | No pipeline DAG | `pipeline/orchestrator.py` declares DAG |
| 16 | No enforcement that L6 emits no signals | Safety Kernel forbidden-field set |
| 17 | No uncertainty feedback | L8 publishes `MetaSignal` to next cycle |
| 18 | No degraded states | `LayerOutput.visibility` field |
| 19 | Vague testing | Test taxonomy: unit / contract / integration / replay-equivalence |
| 20 | No CI/release gates | Documented in `TESTING_STRATEGY.md` |

### Pass 2 (expansion: causal graph, ontology, etc.)

| # | Expansion item | Implementation site |
|---|----------------|---------------------|
| 21 | Causal inference graph | `aquila/causal/` |
| 22 | Liquidity ontology | `aquila/ontology/liquidity.py` |
| 23 | Transition physics engine | `aquila/physics/` |
| 24 | Cross-asset cognition | `aquila/intermarket/` |
| 25 | Data governance / event sourcing | `aquila/governance/`, `aquila/eventstore/` |
| 26 | Cognitive explainability | `aquila/narrative/explainer.py` |
| 27 | Counterfactual simulation | `aquila/simulation/` |
| 28 | Cognitive drift monitor | `aquila/drift/` |
| 29 | Structural ontology system | `aquila/ontology/` |
| 30 | Cognitive query interface | `aquila/query/` |
| 31 | Probabilistic reasoning | `aquila/probabilistic/` |
| 32 | Attention allocator | `aquila/attention/` |
| 33 | Human interpretation layer | `aquila/narrative/` |
| 34 | Research experiment harness | `aquila/experiments/` |
| 35 | Bounded contexts / immutable comms | enforced by `LayerOutput.model_config["frozen"]=True` + event bus contract |
| 36 | Versioned cognitive protocols | `aquila/protocols/` |
| 37 | Cognitive failure-state framework | `aquila/failure/` |
| 38 | Cognitive resource governance | `aquila/governance/resources.py` |
| 39 | Cognitive security boundaries | `aquila/security/` |
| 40 | Distributed runtime spec | `aquila/runtime/` + `docs/RUNTIME.md` |
| 41 | Real-time ingestion spec | `aquila/ingestion/` + `docs/INGESTION.md` |
| 42 | Scientific validation | `aquila/validation/` |

### Pass 3 — still missing after expansion (closed in this PR)

| # | Still-missing item | Closure |
|---|--------------------|---------|
| 43 | Asset/instrument master | `aquila/ingestion/instruments.py` |
| 44 | Canonical clock authority | `aquila/core/clock.py` (`Clock` interface + `WallClock` + `ReplayClock`) |
| 45 | Numerical-precision policy | `aquila/core/numeric.py` (Decimal context, NaN guard) |
| 46 | Cold-start / warm-up policy | `aquila/core/warmup.py` |
| 47 | Output TTL / freshness | `LayerOutput.ttl_seconds` |
| 48 | Idempotency keys for ingestion | `RawEvent.idempotency_key` |
| 49 | Memory eviction policy | `aquila/memory/eviction.py` |
| 50 | Bounded reflexivity (L8 self-bound) | `aquila/meta/reflexivity.py` (max depth = 1) |
| 51 | Synthetic-event lineage tag | `RawEvent.origin: real \| synthetic \| replay` |
| 52 | Data-source trust score | `aquila/ingestion/trust.py` |
| 53 | Assumption registry | `aquila/governance/assumptions.py` |
| 54 | Evidence citations | `LayerOutput.evidence: list[EventRef]` |
| 55 | IPC transport interface | `aquila/runtime/transport.py` |
| 56 | Layer SLA / latency budget | `aquila/config/sla.py` |
| 57 | Load-shedding policy | `aquila/failure/load_shed.py` |
| 58 | Health probes | `aquila/api/routes/health.py` |
| 59 | Replay slicing | `aquila/replay/slicer.py` |
| 60 | CQRS read-model separation | `aquila/query/projections.py` |
| 61 | Ontology editorial governance | `aquila/ontology/registry.py` |
| 62 | Audit-log immutability proof | `aquila/observability/audit.py` (hash-chain) |
| 63 | Falsifiability contract | `aquila/validation/falsifiability.py` |
| 64 | Cognitive A/B / shadow exec | `aquila/experiments/shadow.py` |
| 65 | Snapshot / checkpoint format | `aquila/governance/snapshots.py` |
| 66 | Cognition export format | `aquila/governance/export.py` (JSON-LD) |
| 67 | Analyst feedback intake (read-only) | `aquila/api/routes/feedback.py` (annotation-only, no cognition mutation) |

---

## Inviolable non-goals (reaffirmed across all passes)

The system MUST NOT:
- autonomously place trades
- emit buy/sell signals or directional forecasts
- optimize for PnL
- self-generate execution logic
- bypass uncertainty thresholds
- suppress contradiction reporting
- modify its own code at runtime
- use unrestricted reinforcement learning

These are enforced by the Safety Kernel and verified by contract tests.
