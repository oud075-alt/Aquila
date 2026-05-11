# MSPIS — Market Structural Pathology Intelligence System

> **Mission:** Detect internal market disease *before* price collapse or
> expansion becomes visible.

MSPIS is **not** a trading bot, not a signal generator, not a trend
follower, and not a retail strategy engine. It is a **structural
diagnostician** that thinks like a market pathologist: it builds a model
of what a healthy market *should* look like in the current regime,
measures what the market *actually* did, and quantifies the structural
contradictions that arise.

---

## Core philosophy

```
ANOMALY = EXPECTED_BEHAVIOR - ACTUAL_BEHAVIOR
```

Markets are not categorised as bullish / bearish / sideway. They are
diagnosed for:

* hidden exhaustion
* structural instability
* liquidity fragility
* continuation failure
* volatility stress
* acceptance failure
* behavioural contradiction
* pressure accumulation
* unstable expansion
* manipulation footprints
* pre-collapse structure
* pre-expansion compression
* instability escalation

The output is a `StandardizedDiagnosis` object containing the dominant
disease label, severity (LEVEL 0 → LEVEL 5), per-pathology probability
scores, contradiction scores, structural health, transition state,
escalation risk and a probabilistic structural projection.

---

## Mandatory intelligence flow

The orchestrator (`brain/orchestrator.py`) executes every diagnosis in
the following strict order, with each module participating:

1. **MARKET SENSORY INGESTION** — `brain/sensory/*`
2. **EXPECTED HEALTHY STRUCTURE MODELING** — `brain/expectation/*`
3. **ACTUAL MARKET BEHAVIOR ANALYSIS** — `brain/intelligence/actual_behavior_engine.py`
4. **CONTRADICTION DETECTION** — `brain/intelligence/contradiction_engine.py`
5. **PATHOLOGY SCORING** — `brain/intelligence/market_diagnosis_engine.py` + `brain/pathology/*`
6. **DISEASE CLASSIFICATION** — `brain/intelligence/disease_classifier.py`
7. **STATE TRANSITION ANALYSIS** — `brain/intelligence/state_transition_engine.py`
8. **RISK ESCALATION FORECAST** — `brain/execution/risk_escalation_alert.py` + `brain/execution/scenario_projection.py`
9. **DIAGNOSTIC REPORT GENERATION** — `brain/gpt/*` + `brain/execution/report_generator.py`
10. **MEMORY STORAGE + LEARNING** — `brain/memory_core.py` + `brain/memory/*`

---

## Project layout

```
mspis/
├── api/
│   ├── __init__.py
│   ├── server.py                       # FastAPI app + lifespan
│   └── routes/
│       ├── __init__.py
│       ├── diagnosis_routes.py         # /diagnosis /market/state /pathology /anomaly /stress /report /alerts /memory
│       └── health_routes.py            # /health /health/components
├── brain/
│   ├── __init__.py
│   ├── orchestrator.py                 # MANDATORY INTELLIGENCE FLOW
│   ├── memory_core.py                  # cross-memory coordinator
│   ├── schemas.py                      # StandardizedDiagnosis + sub-objects
│   ├── math_core.py                    # statistical primitives
│   ├── logging_utils.py
│   ├── sensory/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── binance_feed.py
│   │   ├── mt5_feed.py
│   │   ├── tradingview_feed.py
│   │   ├── tick_stream.py
│   │   ├── candle_stream.py
│   │   ├── orderflow_parser.py
│   │   ├── liquidity_map.py
│   │   ├── volatility_tracker.py
│   │   ├── news_stream.py
│   │   └── economic_calendar.py
│   ├── expectation/
│   │   ├── __init__.py
│   │   ├── market_regime_model.py
│   │   ├── healthy_trend_model.py
│   │   ├── continuation_expectation.py
│   │   ├── volatility_expectation.py
│   │   └── expected_behavior_engine.py
│   ├── pathology/
│   │   ├── __init__.py
│   │   ├── anomaly_detector.py
│   │   ├── hidden_exhaustion_model.py
│   │   ├── structural_instability_model.py
│   │   ├── continuation_failure_model.py
│   │   ├── liquidity_fragility_model.py
│   │   ├── stress_escalation_model.py
│   │   ├── acceptance_failure_model.py
│   │   ├── behavioral_divergence_model.py
│   │   ├── pre_collapse_model.py
│   │   └── compression_pressure_model.py
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── actual_behavior_engine.py
│   │   ├── contradiction_engine.py
│   │   ├── disease_classifier.py
│   │   ├── pathology_ranker.py
│   │   ├── confidence_engine.py
│   │   ├── state_transition_engine.py
│   │   └── market_diagnosis_engine.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── vector_memory.py
│   │   ├── pattern_memory.py
│   │   ├── failure_memory.py
│   │   ├── market_history_memory.py
│   │   └── adaptive_memory.py
│   ├── gpt/
│   │   ├── __init__.py
│   │   ├── gpt_reasoning_bridge.py
│   │   ├── market_explainer.py
│   │   └── diagnostic_summary_ai.py
│   └── execution/
│       ├── __init__.py
│       ├── alert_engine.py
│       ├── report_generator.py
│       ├── scenario_projection.py
│       └── risk_escalation_alert.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── api_keys.py
│   └── market_config.py
├── scripts/
│   ├── run_diagnose_once.py
│   └── run_live_loop.py
├── tests/
│   ├── full_pipeline_test.py
│   ├── stress_test.py
│   └── diagnostic_test.py
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Install

Requires **Python 3.12+**.

```bash
git clone <this repo>
cd mspis
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your credentials
```

Notes:

* `MetaTrader5` is Windows-only and is automatically skipped on Linux/Mac.
* The system runs end-to-end without any API key by falling back to a
  deterministic synthetic candle generator. This is for end-to-end
  pipeline exercising only; the diagnosis is structurally meaningful but
  it is *not* live data. To produce live diagnoses fill in real
  credentials in `.env`.

---

## Run

### One-shot diagnosis from CLI

```bash
python scripts/run_diagnose_once.py --symbol BTC/USDT --timeframe 5m
```

### Continuous diagnostic loop

```bash
python scripts/run_live_loop.py --symbol BTC/USDT --timeframe 5m --interval 60
```

### Production API server

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8080
```

Then query:

```bash
curl 'http://localhost:8080/diagnosis?symbol=BTC/USDT&timeframe=5m&include_gpt=false'
curl 'http://localhost:8080/health'
curl 'http://localhost:8080/pathology?symbol=ETH/USDT&timeframe=15m'
curl 'http://localhost:8080/report?symbol=BTC/USDT&timeframe=1h&format=markdown'
```

API endpoints:

| Route                 | Purpose                                                          |
|-----------------------|------------------------------------------------------------------|
| `GET /diagnosis`      | Full standardized diagnosis object                               |
| `GET /market/state`   | Market state + severity + structural health (lightweight)        |
| `GET /pathology`      | Pathology scores + priority-ranked contributors                  |
| `GET /anomaly`        | Contradictions + expectation vs actual                           |
| `GET /stress`         | Stress + liquidity + escalation risk + volatility / instability  |
| `GET /report`         | Markdown or JSON report                                          |
| `GET /alerts`         | Recent structural alerts                                         |
| `GET /memory/recent`  | Recent diagnoses persisted in market history memory              |
| `GET /health`         | Liveness + capability flags                                      |
| `GET /health/components` | Detailed orchestrator component state                          |

Set `MSPIS_API_KEY=<token>` in `.env` to enable bearer auth.

---

## Test

```bash
pytest -q
```

Test suites:

* `tests/full_pipeline_test.py` — end-to-end orchestration sanity.
* `tests/stress_test.py` — concurrency + fault tolerance.
* `tests/diagnostic_test.py` — direct module-level correctness.

---

## Cognitive identity

MSPIS thinks like:

* a market pathologist
* a structural diagnostician
* a behavioural systems analyst
* a regime transition observer
* a probabilistic intelligence engine

It does **not** think like a trader, signal generator, entry optimiser,
or retail strategist. Trade execution is **not** the intelligence
objective.

Pathology severity hierarchy:

| Level     | Label                              |
|-----------|------------------------------------|
| LEVEL 0   | HEALTHY_STRUCTURE                  |
| LEVEL 1   | MINOR_INSTABILITY                  |
| LEVEL 2   | FRAGILE_STRUCTURE                  |
| LEVEL 3   | HIGH_RISK_TRANSITION               |
| LEVEL 4   | PRE_COLLAPSE                       |
| LEVEL 5   | STRUCTURAL_FAILURE                 |

---

## Disclaimer

MSPIS is research / intelligence software. It does not place orders,
does not produce trade signals, and does not optimise win-rate. It
explains structural health and structural disease.
