# AQUILA

**Adaptive Quant Unified Intelligence for Liquidity & Anomaly** — an
institutional-grade market cognition engine. Extends the MSPIS architecture
into a full 8-layer cognitive intelligence system.

> **This is NOT a trading bot, signal generator, or auto-buy/sell predictor.**
> Aquila is a structural pathology intelligence framework and market anomaly
> interpretation system. The Safety Kernel actively rejects any output
> containing trade-signal lexicon.

## Quick start

```bash
pip install --user --break-system-packages -r requirements.txt
python3 -m pytest -q
python3 -m uvicorn aquila.api:create_app --factory --reload
```

Open `http://localhost:8000/docs` for the interactive OpenAPI surface.

Run a single cognitive tick:

```bash
curl -X POST http://localhost:8000/cognition/tick \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","timestamp":"2026-05-11T10:00:00Z","open":100,"high":101,"low":99,"close":100.5,"volume":12}'
```

## Cognitive layers

| # | Layer | Module | Output |
|---|-------|--------|--------|
| 1 | Primitive Metrics | `aquila.primitives` | `PrimitiveSnapshot` |
| 2 | Structural Diagnosis | `aquila.structural` | `StructuralDiagnosis` |
| 3 | Pathology & Contradiction | `aquila.pathology` | `PathologyReport` |
| 4 | Episodic Market Memory | `aquila.memory` | `MemoryRecall` |
| 5 | Temporal Hierarchy Cognition | `aquila.temporal` | `TemporalCognition` |
| 6 | Deception Intelligence | `aquila.deception` | `DeceptionReport` |
| 7 | Regime Mutation Engine | `aquila.regime` | `RegimeMutationReport` |
| 8 | Meta-Cognition | `aquila.meta` | `MetaCognitiveReport` |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full
architectural tree, [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md) for the
per-tick data flow, and [`docs/PROMPT_AUDIT.md`](docs/PROMPT_AUDIT.md)
for the gap audit closing 67 prompt items.

## Supporting subsystems

`ingestion`, `safety`, `pipeline`, `replay`, `narrative`, `causal`,
`ontology`, `physics`, `intermarket`, `governance`, `simulation`,
`drift`, `query`, `probabilistic`, `attention`, `experiments`,
`protocols`, `failure`, `security`, `runtime`, `validation`, `config`,
`observability`.

## Architectural invariants

1. Layers communicate only via immutable `LayerOutput` instances.
2. Safety Kernel rejects every payload containing trade-signal lexicon.
3. Meta recursion depth ≤ 1 (bounded reflexivity).
4. Synthetic-origin events never write the real episodic archive.
5. Audit log is hash-chained and tamper-evident.
6. Replay determinism: `ReplayClock` + read-only memory mode.
7. No self-modifying code, no unrestricted reinforcement learning.

## Honest scope

Layers L1–L8, pipeline, safety, memory, replay, narrative, ingestion,
observability, and the FastAPI surface are **implemented**. The 19
supporting subsystems are **scaffolded** with typed interfaces +
minimal functional implementations. Distributed runtime IPC adapters
(Kafka/NATS/gRPC) and full real-time ingestion gateways are
**specified** (interfaces ship; transports TBD).

See `docs/PROMPT_AUDIT.md` for the full deliverables matrix.

## License

Proprietary.
