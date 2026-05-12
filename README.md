# AQUILA

**Adaptive Quant Unified Interpretation for Liquidity & Anomaly** — a
structural anomaly research platform with deterministic replay. Built on
the MSPIS architecture.

> **This is NOT a trading bot, signal generator, or auto-buy/sell predictor.**
> Aquila is a structural anomaly research platform. The Safety Kernel
> actively rejects any output containing trade-signal lexicon.

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

## Layer modules

| # | Layer | Module | Output |
|---|-------|--------|--------|
| 1 | Primitive Metrics | `aquila.primitives` | `PrimitiveSnapshot` |
| 2 | Structural Diagnosis | `aquila.structural` | `StructuralDiagnosis` |
| 3 | Pathology & Contradiction | `aquila.pathology` | `PathologyReport` |
| 4 | Episodic Market Memory | `aquila.memory` | `MemoryRecall` |
| 5 | Temporal Hierarchy | `aquila.temporal` | `TemporalCognition` |
| 6 | Deception / Trap Heuristics | `aquila.deception` | `DeceptionReport` |
| 7 | Regime Tracking | `aquila.regime` | `RegimeMutationReport` |
| 8 | Meta Aggregation | `aquila.meta` | `MetaCognitiveReport` |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the architectural
tree, [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md) for the per-tick data
flow, and [`docs/PROMPT_AUDIT.md`](docs/PROMPT_AUDIT.md) for the gap
audit table.

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
5. Audit log is hash-chained over both metadata and payload body.
6. Replay determinism: `ReplayClock` + read-only memory mode.
7. No self-modifying code, no unrestricted reinforcement learning.

## Honest scope

Status terms used below:

- **VERIFIED_EMPIRICAL** — code exists AND empirical test asserts behaviour on data.
- **VERIFIED_STRUCTURAL** — code exists AND contract/structural tests pass.
- **SCAFFOLDED** — typed interfaces + minimal pass-through implementation; no empirical validation.

| Layer | Status | Evidence |
|-------|--------|----------|
| L1 Primitives | VERIFIED_STRUCTURAL | contract tests on `PrimitiveSnapshot` shape |
| L2 Structural | VERIFIED_STRUCTURAL | contract tests; thresholds **not calibrated** |
| L3 Disequilibrium (pathology) | SCAFFOLDED | no empirical validation |
| L4 Memory | SCAFFOLDED | no forward outcome attached yet |
| L5 Temporal | SCAFFOLDED | no empirical validation |
| L6 Deception / Trap Heuristics | SCAFFOLDED | no empirical validation |
| L7 Regime Tracking | SCAFFOLDED | no empirical validation |
| L8 Meta Aggregation | SCAFFOLDED | no empirical validation |

## What this system can prove today

The following are asserted by automated tests in this repository:

- **Deterministic replay**: the same `RawEvent` sequence fed twice produces identical layer outputs (`tests/test_replay.py`, `tests/falsification/test_bar_closed_data.py`).
- **Audit chain integrity over payload AND metadata**: tampering confidence, payload body, or `prev_hash` invalidates `AuditLog.verify()` (`tests/test_audit_payload_tamper.py`).
- **Safety field linter**: any payload containing a trade-signal-shaped field (`direction`, `entry`, `target`, etc.) is rejected by `SafetyKernel` (`tests/falsification/test_no_signal_emission.py`).
- **Origin isolation**: ticks with `origin="synthetic"` never write the real memory archive (`tests/falsification/test_origin_isolation.py`).
- **Bounded reflexivity**: `assert_within_bound(depth)` raises for `depth > 1` (`tests/falsification/test_bounded_reflexivity.py`).

## What this system cannot yet prove

- **No detector has been empirically validated on out-of-sample data.** All L2/L3 rule thresholds are hardcoded constants.
- **No anomaly definition has demonstrated lift over a random baseline.** There is no walk-forward backtest harness yet.
- **No forward outcome is attached to any memory episode.** L4 stores diagnoses but no realised return / MAE / MFE.
- **No statistical claim (correlation, lead-lag, cointegration, Bayesian posterior) is computed from real distributions.** Probabilistic / intermarket / causal modules are heuristic.

These limitations are intentional — see `docs/PROMPT_AUDIT.md` and the
`docs/adr/` directory for the policy and roadmap.

## License

Proprietary.
