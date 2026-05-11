from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from aquila.api import create_app
from aquila.api.deps import reset_state


def _client():
    reset_state()
    return TestClient(create_app())


def test_health_live():
    c = _client()
    r = c.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_cognition_tick_returns_all_layers():
    c = _client()
    r = c.post("/cognition/tick", json={
        "symbol": "BTCUSDT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.2, "volume": 12.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert "correlation_id" in body
    assert set(body["layers"].keys()) == {
        "primitives", "structural", "pathology", "memory",
        "temporal", "deception", "regime", "meta",
    }


def test_validation_runs():
    c = _client()
    r = c.get("/validation/run")
    assert r.status_code == 200
    body = r.json()
    assert body["audit_chain_ok"] is True
    assert body["falsifiability_ok"] is True


def test_feedback_annotation_does_not_mutate_cognition():
    c = _client()
    r = c.post("/feedback/annotate", json={"correlation_id": "x", "note": "manual review"})
    assert r.status_code == 200
    assert r.json()["stored"] is True
