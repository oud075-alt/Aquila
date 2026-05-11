# Module Dependency Graph

```
core/  ←─ everything depends on core
   │
   ├── ingestion/    (Layer 0)
   ├── primitives/   (Layer 1)  → core
   ├── structural/   (Layer 2)  → core + primitives
   ├── pathology/    (Layer 3)  → core + structural + primitives
   ├── memory/       (Layer 4)  → core + structural + pathology + primitives
   ├── temporal/     (Layer 5)  → core + structural
   ├── deception/    (Layer 6)  → core + structural + pathology + primitives
   ├── regime/       (Layer 7)  → core + pathology + primitives
   ├── meta/         (Layer 8)  → core + (all L1-L7 read-only via ctx)
   │
   ├── pipeline/     orchestrator → all 8 layers + safety + bus + observability
   ├── replay/       → pipeline + ingestion + memory.replay_integration + core.clock
   ├── narrative/    → core + all 8 layer schemas (read-only)
   │
   ├── causal/       → core + (all 8 layer schemas read-only)
   ├── ontology/     → core + structural + pathology + deception + regime schemas
   ├── physics/      → core + structural
   ├── intermarket/  → core + regime
   ├── governance/   → core + base.LayerOutput
   ├── simulation/   → replay + ingestion
   ├── drift/        → core + meta + structural + memory schemas
   ├── query/        → governance.eventstore + causal + core
   ├── probabilistic/→ core
   ├── attention/    → core
   ├── experiments/  → pipeline + core
   ├── protocols/    → core
   ├── failure/      → core + meta + pathology + regime schemas
   ├── security/     → observability.audit + ontology + protocols
   ├── runtime/      → core + observability.telemetry
   ├── validation/   → governance.assumptions + observability.audit + ontology + protocols + safety
   ├── config/       → core
   ├── safety/       → core
   ├── observability/→ core
   └── api/          → pipeline + governance + ontology + safety + protocols + narrative + intermarket + simulation + query + replay
```

## Acyclicity

The dependency graph is a strict DAG. Higher-numbered cognitive layers
never import from layers below them in the cognition order; they receive
upstream outputs through `LayerContext.upstream_outputs` instead.
