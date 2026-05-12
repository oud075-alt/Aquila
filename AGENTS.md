# AGENTS.md

## Cursor Cloud specific instructions

### Repository structure

The `main` branch contains only a bootstrapped README. All application code lives on feature branches:

| Branch | Product | Notes |
|---|---|---|
| `cursor/mspis-foundation-9c24` | MSPIS v0.1 (foundation) | Cleanest branch: CI, strict mypy, comprehensive tests. **Recommended base for new work.** |
| `cursor/aquila-mspis-cognitive-architecture-8d4c` | Aquila v0.1.0 (8-layer cognition) | Extended architecture with 19+ subsystems. Less strict lint/type-checking. |
| `cursor/mspis-build-9f01` | MSPIS v1.0 build | Heavier deps (ML stack). Has release zip + scripts. |
| `cursor/m0-*`, `cursor/m1-*`, `cursor/m3-*` | Incremental improvements on Aquila | Each branch extends the Aquila base. |

### Running on the mspis-foundation branch

This is the most CI-complete branch. Standard workflow:

```bash
pip install -e ".[dev]"
python3 -m tests.fixtures.generate_btcusdt_sample   # regenerate test fixture
ruff check .                                         # lint
mypy core brain api                                  # strict type-check
pytest -q                                            # all tests (~37, takes ~90s)
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload   # dev server
```

Key API endpoints: `GET /`, `GET /health`, `GET /system/status`, `POST /system/replay`, `GET /diagnosis`, `GET /pathology`, `GET /contradictions`, `GET /risk`, `GET /regime`, `GET /confidence`, `GET /metrics`.

### Running on the Aquila branch

```bash
pip install -e ".[dev]"
ruff check .      # has pre-existing lint warnings (F821, E702, etc.)
mypy aquila       # has pre-existing type errors (11 errors in 7 files)
pytest -q         # all tests (~31, runs in <1s)
uvicorn aquila.api.app:app --host 0.0.0.0 --port 8000 --reload   # dev server
```

Key API endpoints: `GET /health/live`, `GET /health/ready`, `POST /cognition/tick`, `GET /cognition/lifecycle/{id}`, and routes under `/memory`, `/query`, `/replay`, `/simulation`, `/validation`, `/narrative`, `/intermarket`, `/feedback`.

### Gotchas

- **`python` vs `python3`:** The VM has `python3` on PATH but not `python`. Use `python3` for scripts.
- **PATH for pip-installed tools:** Tools like `ruff`, `mypy`, `pytest`, `uvicorn` install to `~/.local/bin`. Ensure `export PATH="$HOME/.local/bin:$PATH"` is set.
- **Test fixture generation:** On `mspis-foundation`, `pytest` requires the Parquet fixture at `tests/fixtures/btcusdt_1m_sample.parquet`. Regenerate with `python3 -m tests.fixtures.generate_btcusdt_sample` if missing.
- **No external services needed:** All external deps (Redis, OpenAI, Binance, ChromaDB) gracefully degrade. The system runs fully in-process with SQLite + synthetic data for development/testing.
- **Aquila lint/type issues are pre-existing:** The Aquila branch has known ruff and mypy issues that exist in the committed code. These are not regressions.
- **mspis-foundation tests take ~90s:** Most time is in the integration/replay tests. Use `pytest -q tests/test_schemas.py` for fast iteration.
