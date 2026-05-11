# MSPIS — Market Structural Pathology Intelligence System

> Structural market cognition and pathology intelligence.
> **Not** a trading bot. **Not** a signal generator. **Not** an indicator collection.

MSPIS analyzes market *structural health* — entropy escalation, continuation
decay, liquidity fragility, dispersion shocks, volatility disorder, and
autocorrelation breakdown — and reasons about regime state, contradictions
in diagnosis, escalation risk, and defensive posture.

The repository is the output: deterministic, auditable, replayable.

---

## Anti-Drift Boundary (Appendix I + Y + P)

MSPIS output schemas and API responses **must not** contain:

```
buy   sell   long   short
entry_price   exit_price
stop_loss   take_profit
position_size   trade_signal
```

These names are CI-enforced in `tests/test_behavior_boundary.py`. Violations
fail the build.

---

## Architecture

```
core/
  schemas/         Phase 0A   versioned Pydantic v2 contracts
  ingestion/       Phase 0B   replay + live adapters (Parquet default)
  pathology/       Phase 0C   6 primitives + structural state classifier
  contradiction/   Phase 0D   matrix + validator + confidence aggregator
  orchestrator/    Phase 0E   single authority; sequencing + state bus
  persistence/     Phase 0F   SQLite metadata + Parquet time-series
  observability/   Phase 0G   structlog + metrics + health
brain/
  decision_engine.py     Phase 1
  context_fusion.py      Phase 2
  strategy_router.py     Phase 3
  risk_intelligence.py   Phase 4
  adaptive_learning.py   Phase 5
api/                     Phase 0H   FastAPI surface
docs/decisions/                     ADRs (Appendix L escape hatch)
tests/                              pytest suite + boundary + replay
```

---

## Determinism (Appendix S)

Replay mode must be byte-identical for the same input parquet.

Required environment when running replay / tests:

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
```

These are also exported by `core.observability.runtime.lock_determinism()`
which is called by the replay adapter on startup.

---

## Install

```bash
pip install -e .[dev]
```

## Run replay

```bash
python -m core.ingestion.replay_adapter \
    --parquet tests/fixtures/btcusdt_1m_sample.parquet
```

## Run API

```bash
uvicorn api.main:app --reload
```

## Tests

```bash
pytest
ruff check .
mypy .
```

---

## Scope Lock (Appendix Q)

Phase 0 is **single-symbol** — `BTCUSDT`. Cross-asset is forbidden until
single-symbol deterministic stability is validated.

## Liquidity Lock (Appendix T)

Phase 0 liquidity analysis uses **OHLCV-derived proxies only**. L2 orderbook
ingestion is forbidden in Phase 0.

## Learning Lock (Appendix D)

Adaptive learning uses **Bayesian posterior updates + EWMA reliability
calibration + replay-based episodic memory** only. No gradient descent,
no self-modifying architecture, no autonomous code generation.
