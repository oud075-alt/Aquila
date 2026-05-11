# Testing Strategy

## Test taxonomy

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | `tests/test_layers.py` | Each cognitive layer produces a valid `LayerOutput` for representative inputs |
| Safety | `tests/test_safety.py` | Safety Kernel rejects forbidden-field payloads; deception safety adapter blocks signals |
| Pipeline | `tests/test_pipeline.py` | DAG runs end-to-end; audit chain stays valid; lifecycle is emitted |
| Memory | `tests/test_memory.py` | JSONL store round-trips; synthetic-origin events never write real archive |
| Replay | `tests/test_replay.py` | Two runs of the same event sequence produce identical confidences (replay-equivalence) |
| Subsystems | `tests/test_subsystems.py` | Each scaffolded subsystem produces a valid result; narrative emits no signal fields; audit log detects tampering |
| API | `tests/test_api.py` | Each FastAPI endpoint returns expected schema |

## Quality gates (recommended for CI)

1. `pytest -q` — all tests pass
2. `mypy aquila/` — strict types (CI gate optional in this PR)
3. `ruff check aquila/` — lint
4. **Replay-equivalence**: golden replay fixture run twice must yield byte-identical `LayerOutput.confidence` and `LayerOutput.payload` for every layer
5. **Safety contract test**: programmatically attempt to construct a layer output with each forbidden field; Safety Kernel must reject 100%
6. **Audit immutability test**: mutate any record in `AuditLog._records` → `verify()` must return False

## Falsifiability commitments

Every assumption in `governance/assumptions.py` declares a `falsifiable_by`
field. CI may enforce that no assumption has an empty falsifier (already
covered by `validation/falsifiability.py`).

## What's NOT tested in this PR

- Distributed runtime under load (no transport adapters yet)
- Long-horizon (months-of-data) calibration drift
- Multi-symbol intermarket cognition under skewed data
- API auth (not in scope — would be added in a separate PR)
