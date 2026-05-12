"""Falsification test for Assumption ``deception.no_signal_emission``.

Claim: the Safety Kernel rejects any layer output whose payload contains
a trade-signal-shaped field. If the kernel ever passes a payload with
``direction``, ``entry``, etc., the non-trading mandate is violated.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName, Symbol
from aquila.safety import SafetyKernel


class _ForbiddenPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    direction: str = "long"


class _CleanPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    note: str = "ok"


def _output(payload):
    return LayerOutput(
        layer=LayerName.DECEPTION,
        symbol=Symbol("X"),
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        correlation_id="c",
        payload=payload,
    )


def test_safety_kernel_rejects_signal_field():
    kernel = SafetyKernel()
    bad = _output(_ForbiddenPayload())
    verdict = kernel.check(bad)
    assert verdict.ok is False
    assert verdict.reason and "forbidden_field" in verdict.reason

    good = _output(_CleanPayload())
    assert kernel.check(good).ok is True
