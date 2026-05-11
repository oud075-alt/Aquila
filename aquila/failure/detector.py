from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName
from aquila.failure.schemas import FailureState, FailureStateReport


class FailureStateDetector:
    def detect(self, outputs: dict[LayerName, LayerOutput]) -> FailureStateReport:
        reasons: list[str] = []
        meta = outputs.get(LayerName.META)
        path = outputs.get(LayerName.PATHOLOGY)
        reg = outputs.get(LayerName.REGIME)

        state = FailureState.NORMAL
        if meta is not None and meta.payload.uncertainty.total > 0.85:  # type: ignore[attr-defined]
            state = FailureState.UNCERTAINTY_OVERFLOW
            reasons.append("uncertainty_overflow")
        if path is not None and path.payload.aggregate_contradiction_score > 0.85:  # type: ignore[attr-defined]
            state = FailureState.CONTRADICTION_SATURATION
            reasons.append("contradiction_saturation")
        if meta is not None and len(meta.payload.low_visibility_layers) >= 3:  # type: ignore[attr-defined]
            state = FailureState.LOW_VISIBILITY_LOCKDOWN
            reasons.append("low_visibility_lockdown")
        if reg is not None and reg.payload.instability_score > 0.85:  # type: ignore[attr-defined]
            state = FailureState.INSTABILITY_ESCALATION
            reasons.append("instability_escalation")

        partial = state != FailureState.NORMAL
        return FailureStateReport(state=state, reasons=reasons, recommend_partial_reasoning=partial)
