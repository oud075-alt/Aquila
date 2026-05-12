"""Empirical proof that the audit chain detects three tamper modes:
confidence (metadata), payload body, and prev_hash (chain header).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName, Symbol, utcnow
from aquila.observability.audit import AuditLog


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True)
    v: int = 0
    note: str = "ok"


def _build_log() -> AuditLog:
    log = AuditLog()
    for i in range(3):
        out = LayerOutput(
            layer=LayerName.PRIMITIVES,
            symbol=Symbol("X"),
            timestamp=utcnow(),
            correlation_id="c",
            payload=_Payload(v=i, note="ok"),
        )
        log.append(out)
    assert log.verify()
    return log


def test_tamper_confidence_invalidates_chain():
    log = _build_log()
    log._records[1] = log._records[1].model_copy(update={"confidence": 0.42})
    assert not log.verify()


def test_tamper_payload_field_invalidates_chain():
    """Re-issue the same record but with a different payload_hash field."""
    log = _build_log()
    forged_hash = "f" * 64
    assert log._records[1].payload_hash != forged_hash
    log._records[1] = log._records[1].model_copy(update={"payload_hash": forged_hash})
    assert not log.verify()


def test_tamper_prev_hash_invalidates_chain():
    log = _build_log()
    log._records[2] = log._records[2].model_copy(update={"prev_hash": "0" * 64})
    assert not log.verify()


def test_clean_chain_verifies():
    log = _build_log()
    assert log.verify()
    assert len(log) == 3
    for r in log:
        assert r.payload_hash and len(r.payload_hash) == 64
        assert r.record_hash and len(r.record_hash) == 64
