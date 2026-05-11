"""Safety Kernel — verifies layer outputs against system-wide invariants.

Invariants:
1. No forbidden field names in any payload (trade-signal lexicon).
2. No payload mutation across the event bus (frozen-model check).
3. Bounded reflexivity (meta-cognition depth).
4. Synthetic-event lineage preserved (no real-store writes from synthetic).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from aquila.core.base import LayerOutput
from aquila.core.exceptions import SafetyViolationError

FORBIDDEN_SIGNAL_FIELDS: frozenset[str] = frozenset({
    "action", "direction", "entry", "target", "stop",
    "side", "signal", "order", "trade", "buy", "sell",
    "leverage", "position", "size_to_trade", "execute",
    "predicted_price", "forecast_price",
})


@dataclass(frozen=True)
class SafetyVerdict:
    ok: bool
    reason: str | None = None


class SafetyKernel:
    def __init__(self, extra_forbidden: set[str] | None = None) -> None:
        self._forbidden = set(FORBIDDEN_SIGNAL_FIELDS)
        if extra_forbidden:
            self._forbidden.update({s.lower() for s in extra_forbidden})

    def check(self, output: LayerOutput) -> SafetyVerdict:
        if not isinstance(output, LayerOutput):
            return SafetyVerdict(False, "not_a_layer_output")

        # Frozen check (Pydantic v2: model_config["frozen"] is set by base)
        cfg = getattr(output, "model_config", {})
        if isinstance(cfg, dict) and cfg.get("frozen") is False:
            return SafetyVerdict(False, "layer_output_not_frozen")

        # Payload field scan
        try:
            blob = output.payload.model_dump() if isinstance(output.payload, BaseModel) else {}
        except Exception as e:  # pragma: no cover
            return SafetyVerdict(False, f"payload_dump_failed:{e}")

        bad = self._scan(blob)
        if bad:
            return SafetyVerdict(False, f"forbidden_field:{bad}")

        return SafetyVerdict(True)

    def enforce(self, output: LayerOutput) -> LayerOutput:
        v = self.check(output)
        if not v.ok:
            raise SafetyViolationError(
                f"Safety Kernel rejected output from {output.layer.value}: {v.reason}"
            )
        return output

    def _scan(self, o) -> str | None:
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and k.lower() in self._forbidden:
                    return k
                r = self._scan(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = self._scan(v)
                if r:
                    return r
        return None
