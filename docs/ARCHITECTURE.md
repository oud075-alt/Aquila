# AQUILA / MSPIS Cognitive Architecture

> **Not a trading bot. Not a signal generator. Not an auto-buy/sell predictor.**
> A market cognition engine, a structural pathology intelligence framework,
> and a market anomaly interpretation system.

## 1. Architecture tree

```
aquila/
├── core/                Shared kernel (types, base, clock, numeric, confidence, warmup)
├── ingestion/           Layer 0 — adapters, normalizer, instruments, trust, schemas
├── primitives/          Layer 1 — Primitive Metrics
├── structural/          Layer 2 — Structural Diagnosis
├── pathology/           Layer 3 — Pathology & Contradiction (+ confidence aggregator)
├── memory/              Layer 4 — Episodic Market Memory
├── temporal/            Layer 5 — Temporal Hierarchy Cognition
├── deception/           Layer 6 — Deception Intelligence (with safety adapter)
├── regime/              Layer 7 — Regime Mutation Engine
├── meta/                Layer 8 — Meta-Cognition (bounded reflexivity)
├── pipeline/            DAG orchestrator + event bus + lifecycle
├── replay/              Deterministic replay runner + slicer + replay context
├── narrative/           Analyst-readable explainer (no signals)
├── causal/              Event-level causal graph engine
├── ontology/            Versioned ontology registry + liquidity ontology
├── physics/             State-transition physics (velocity, accel, collapse)
├── intermarket/         Cross-asset cognition (disagreement, migration, contagion)
├── governance/          EventStore, assumptions, snapshots, export, resources
├── simulation/          Counterfactual + scenario stress (synthetic-origin tagged)
├── drift/               Calibration / contamination / overfitting / fixation
├── query/               CQRS projections + cognitive query engine
├── probabilistic/       Heuristic score fuser + evidence weighting (legacy "Bayesian" alias deprecated; see ADR-0006)
├── attention/           Salience allocator
├── experiments/         Experiment tracker + shadow executor
├── protocols/           Versioned schema compatibility matrix
├── failure/             Failure-state detector + load-shed policy
├── security/            Integrity validator (audit + ontology + protocols)
├── runtime/             EventTransport interface + scheduler + supervisor
├── validation/          Scientific validation suite + falsifiability
├── config/              Per-layer settings + per-symbol overrides + SLAs
├── safety/              Centralized Safety Kernel
├── observability/       Structured logger + hash-chained audit + telemetry
└── api/                 FastAPI app + routes
```

## 2. Cognitive DAG

```
[Layer 0 Ingestion: OHLCV / OrderFlow / Macro]
                │
                ▼
        L1 Primitives ────────────────────────────────┐
                │                                     │
                ▼                                     │
        L2 Structural Diagnosis ──────────────────────┤
                │                                     │
                ▼                                     │
        L3 Pathology & Contradiction ─────────────────┤
                │                                     │
                ├──────► L4 Episodic Market Memory ───┤
                ├──────► L5 Temporal Hierarchy ───────┤
                ├──────► L6 Deception Intelligence ───┤
                └──────► L7 Regime Mutation ──────────┤
                                                      │
                                                      ▼
                                              L8 Meta-Cognition
                                                      │
                                                      ▼
                                              Narrative Emitter
                                              + Causal Graph
                                              + Attention Allocator
                                              + Failure Detector
                                              + Drift Monitor
                                              + Intermarket Engine
                                              ─────────────────►  Event Store / Audit Log
```

## 3. Bounded contexts — invariants

| Invariant | Enforcement |
|-----------|-------------|
| Layers communicate only via `LayerOutput` instances | Type system + event bus contract |
| `LayerOutput` is immutable | `model_config["frozen"] = True` |
| No trade-signal lexicon in any payload | `SafetyKernel` forbidden-field scan |
| Meta recursion depth ≤ 1 | `meta.reflexivity.assert_within_bound` |
| Synthetic origin never writes real archive | `EpisodicMemoryLayer.write_on_real` + `ctx.origin` check |
| Audit log is tamper-evident | SHA-256 hash chain in `observability.audit.AuditLog` |
| Replay determinism | `ReplayClock` + read-only memory mode |

## 4. Confidence propagation

`aquila.core.confidence.ConfidenceCalculus`:

- `combine_independent(values)` — probabilistic OR: `1 - Π(1 - vᵢ)`
- `conjunction(values)` — probabilistic AND: `Π vᵢ`
- `decay(value, age, half_life)` — `value · 0.5^(age/half_life)`
- `weighted_mean(pairs)` — `Σ wᵢ·cᵢ / Σ wᵢ`
- `contradiction_penalty(c, x)` — `c · (1 - x)`

L8 uses these to fuse layer confidences into a single `cognitive_health` score.

## 5. Visibility semantics

`LayerOutput.visibility ∈ {full, partial, degraded, blind}`. L8 consumes
visibility to compute `UncertaintyModel.visibility_penalty`. ≥ 2 degraded
or blind layers triggers `MetaSignal.elevated_uncertainty`, which the
orchestrator carries into the next cycle as `ctx.meta_signal`.
