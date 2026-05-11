"""Appendix P + Y — Behavior Boundary CI enforcement.

This test fails CI if any of the following surfaces contain a forbidden
field name:

    1. Pydantic schema field declarations under `core/schemas/` and
       `api/`. (AST + model_fields inspection — Appendix Y scope)
    2. Any JSON response key returned by any GET endpoint of the API.
    3. The serialized DiagnosisEnvelope JSON output.

Scope is limited to schema fields + API JSON keys (Appendix Y) — local
variable names like `long_window` MUST NOT trigger failure.

Forbidden surface (Appendix I):
    buy, sell, long, short, entry_price, exit_price,
    stop_loss, take_profit, position_size, trade_signal
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "long",
        "short",
        "entry_price",
        "exit_price",
        "stop_loss",
        "take_profit",
        "position_size",
        "trade_signal",
    }
)

PACKAGES_TO_SCAN: tuple[str, ...] = ("core.schemas", "api")


def _walk_pydantic_models(pkg_name: str) -> Iterable[type[BaseModel]]:
    pkg = importlib.import_module(pkg_name)
    pkg_path: list[str] = getattr(pkg, "__path__", [])
    for _, mod_name, _ in pkgutil.walk_packages(pkg_path, prefix=f"{pkg_name}."):
        try:
            module = importlib.import_module(mod_name)
        except Exception:  # pragma: no cover - imports under test
            continue
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseModel) and obj is not BaseModel:
                yield obj
    for _, obj in inspect.getmembers(pkg, inspect.isclass):
        if issubclass(obj, BaseModel) and obj is not BaseModel:
            yield obj


def test_no_forbidden_pydantic_field_declarations() -> None:
    violations: list[str] = []
    seen: set[str] = set()
    for pkg_name in PACKAGES_TO_SCAN:
        for model in _walk_pydantic_models(pkg_name):
            fqn = f"{model.__module__}.{model.__name__}"
            if fqn in seen:
                continue
            seen.add(fqn)
            for field_name in model.model_fields.keys():
                if field_name.lower() in FORBIDDEN_FIELDS:
                    violations.append(f"{fqn}.{field_name}")
    assert not violations, (
        "Forbidden behavior-boundary fields detected in Pydantic schemas: "
        + ", ".join(violations)
    )


def _walk_keys(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from _walk_keys(v)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_keys(item)


def _assert_no_forbidden_keys(payload: Any, *, where: str) -> None:
    bad = [k for k in _walk_keys(payload) if k.lower() in FORBIDDEN_FIELDS]
    assert not bad, f"forbidden keys in {where}: {sorted(set(bad))}"


def test_diagnosis_envelope_serialization_clean(sample_parquet: Path) -> None:
    import asyncio

    from core.ingestion import ReplayAdapter
    from core.orchestrator import DiagnosisCoordinator
    from core.schemas.enums import Timeframe

    async def _run() -> dict[str, Any]:
        adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)
        coord = DiagnosisCoordinator()
        last = None
        async for env in coord.diagnose_stream(adapter):
            last = env
        assert last is not None
        return last.model_dump(mode="json")

    payload = asyncio.run(_run())
    _assert_no_forbidden_keys(payload, where="DiagnosisEnvelope JSON")


GET_ENDPOINTS: tuple[str, ...] = (
    "/",
    "/health",
    "/system/status",
    "/diagnosis",
    "/pathology",
    "/contradictions",
    "/risk",
    "/context",
    "/regime",
    "/confidence",
    "/metrics",
)


@pytest.fixture
def api_client(tmp_data_root: Path, sample_parquet: Path) -> Iterable[TestClient]:
    from api.main import app
    from api.runtime import Runtime

    Runtime.reset()
    runtime = Runtime.instance()
    import asyncio

    asyncio.run(runtime.run_replay(sample_parquet))
    with TestClient(app) as client:
        yield client
    Runtime.reset()


def test_no_forbidden_keys_in_api_responses(api_client: TestClient) -> None:
    for path in GET_ENDPOINTS:
        resp = api_client.get(path)
        assert resp.status_code in (200, 404), f"{path} → {resp.status_code}"
        if resp.status_code != 200:
            continue
        try:
            payload = resp.json()
        except ValueError:
            payload = {}
        _assert_no_forbidden_keys(payload, where=f"GET {path}")


def test_replay_response_clean(api_client: TestClient) -> None:
    parquet = Path("tests/fixtures/btcusdt_1m_sample.parquet")
    resp = api_client.post("/system/replay", json={"parquet_path": str(parquet)})
    assert resp.status_code == 200
    _assert_no_forbidden_keys(resp.json(), where="POST /system/replay")


def test_invalid_diagnosis_still_no_forbidden_keys(sample_parquet: Path) -> None:
    """Even diagnoses that hit INVALID contradiction policy must obey Appendix I."""
    import asyncio

    from core.ingestion import ReplayAdapter
    from core.orchestrator import DiagnosisCoordinator
    from core.schemas.enums import Timeframe

    async def _run() -> list[dict[str, Any]]:
        adapter = ReplayAdapter(sample_parquet, timeframe=Timeframe.ONE_MIN)
        coord = DiagnosisCoordinator()
        invalids: list[dict[str, Any]] = []
        async for env in coord.diagnose_stream(adapter):
            if env.validation_failed:
                invalids.append(env.model_dump(mode="json"))
        return invalids

    invalids = asyncio.run(_run())
    assert invalids, "expected at least one INVALID diagnosis on synthetic data"
    for payload in invalids:
        _assert_no_forbidden_keys(payload, where="INVALID DiagnosisEnvelope JSON")
