"""Per-layer safety adapter for Deception. Delegates to the global Safety
Kernel but exposes the local invariants for this layer.

Layer 6 must NEVER emit fields resembling: action, direction, entry,
target, stop, side, signal, order, trade.
"""

from __future__ import annotations

from aquila.core.exceptions import SafetyViolationError
from aquila.deception.schemas import DeceptionReport

LOCAL_FORBIDDEN = {
    "action", "direction", "entry", "target", "stop",
    "side", "signal", "order", "trade", "buy", "sell",
}


def assert_no_signal(report: DeceptionReport) -> None:
    """Inspect serialized payload for forbidden field names — defense in depth."""
    blob = report.model_dump()

    def _walk(o):
        if isinstance(o, dict):
            for k in o:
                if k.lower() in LOCAL_FORBIDDEN:
                    raise SafetyViolationError(
                        f"DeceptionReport contains forbidden field '{k}'"
                    )
                _walk(o[k])
        elif isinstance(o, list):
            for v in o:
                _walk(v)

    _walk(blob)
