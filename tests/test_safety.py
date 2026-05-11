from __future__ import annotations

import pytest

from aquila.core.base import LayerOutput
from aquila.core.exceptions import SafetyViolationError
from aquila.core.types import LayerName, Symbol, utcnow
from aquila.deception.schemas import DeceptionReport
from aquila.deception.safety import assert_no_signal
from aquila.safety import SafetyKernel
from pydantic import BaseModel, ConfigDict


def test_safety_kernel_accepts_clean_deception_report():
    rep = DeceptionReport(deception_probability=0.4)
    assert_no_signal(rep)


def test_safety_kernel_rejects_forbidden_field_payload():
    class BadPayload(BaseModel):
        model_config = ConfigDict(frozen=True)
        action: str = "buy"

    out = LayerOutput(
        layer=LayerName.DECEPTION,
        symbol=Symbol("BTCUSDT"),
        timestamp=utcnow(),
        correlation_id="c1",
        payload=BadPayload(),
    )
    kernel = SafetyKernel()
    v = kernel.check(out)
    assert not v.ok
    assert "action" in (v.reason or "")
    with pytest.raises(SafetyViolationError):
        kernel.enforce(out)
