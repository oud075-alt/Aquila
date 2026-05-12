# ADR-0000 — Bootstrap Decisions

Status: Accepted
Date: 2026-05-11

## Context

The MSPIS specification (Phase 0 + Appendices A–AA) does not pin every
runtime detail. Per Appendix L (Escape Hatch), this ADR records the
most-defensible deterministic defaults adopted at bootstrap.

## Decisions

### 1. Repository layout

Flat package layout with top-level packages `core/`, `brain/`, `api/`,
matching the literal paths used throughout the specification. No `src/`
layout. Tests live in `tests/`. ADRs in `docs/decisions/`.

### 2. Dependency manager

Plain `pip` with `pyproject.toml` (PEP 621). No poetry/uv lock to keep
the substrate minimal and reproducible across CI runners.

### 3. Async runtime

`asyncio` only. `anyio` is permitted for primitives but the orchestrator
runs on a single asyncio event loop.

### 4. ADR numbering

Sequential, zero-padded to 4 digits, kebab-case slug.
`docs/decisions/ADR-XXXX-slug.md`.

### 5. Replay-first

Phase 0 ships with Parquet replay as the primary path. Live websocket
adapter exists but is not the validation substrate.

### 6. Symbol scope

Per Appendix Q: `BTCUSDT` only. Schemas carry a `symbol` field for
future scope expansion but the orchestrator validates single-symbol
operation in Phase 0.

### 7. SLO target (informational)

Diagnosis latency target: < 250 ms per bar on a single core for the
deterministic replay path. This is informational; CI does not gate on
latency.

### 8. Schema immutability

All Pydantic schemas use `model_config = ConfigDict(frozen=True,
extra="forbid", strict=True)` to prevent silent drift and bypass of
schema validation.

### 9. Persistence retention

Phase 0 does not auto-prune. Persistence is append-only with explicit
retention to be decided in a future ADR when memory growth becomes
material.

### 10. CI gates

`ruff check`, `mypy --strict`, `pytest` are mandatory. Behavior boundary
test (Appendix P) is mandatory. Determinism replay test (Appendix S)
is mandatory.

## Consequences

- All future ADRs reference and may override these defaults.
- Module authors who need to deviate must open a new ADR.
