from __future__ import annotations

from collections import deque

from aquila.core.base import LayerOutput
from aquila.core.numeric import safe_prob
from aquila.core.types import LayerName
from aquila.drift.schemas import DriftReport


class DriftMonitor:
    def __init__(self, window: int = 200) -> None:
        self._meta_uncertainty: deque[float] = deque(maxlen=window)
        self._structural_state_history: deque[str] = deque(maxlen=window)
        self._synthetic_writes: int = 0
        self._real_writes: int = 0

    def observe(self, outputs: dict[LayerName, LayerOutput]) -> DriftReport:
        meta = outputs.get(LayerName.META)
        struct = outputs.get(LayerName.STRUCTURAL)
        mem = outputs.get(LayerName.MEMORY)
        if meta is not None:
            self._meta_uncertainty.append(meta.payload.uncertainty.total)  # type: ignore[attr-defined]
        if struct is not None:
            self._structural_state_history.append(struct.payload.state.value)  # type: ignore[attr-defined]
        if mem is not None:
            payload = mem.payload
            if getattr(payload, "written", False):
                if mem.origin == "real":
                    self._real_writes += 1
                else:
                    self._synthetic_writes += 1

        notes: list[str] = []
        # calibration_decay: rising uncertainty trend
        cd = 0.0
        if len(self._meta_uncertainty) >= 20:
            recent = list(self._meta_uncertainty)[-20:]
            cd = safe_prob(max(0.0, sum(recent) / 20.0))
            if cd > 0.6:
                notes.append("uncertainty_trend_high")
        # memory_contamination: any synthetic-origin write reaching real archive
        mc = 0.0
        if self._synthetic_writes > 0:
            mc = safe_prob(self._synthetic_writes / max(1, self._synthetic_writes + self._real_writes))
            notes.append("synthetic_writes_observed")
        # overfitting_drift: structural state diversity collapsing
        od = 0.0
        if len(self._structural_state_history) >= 30:
            recent = list(self._structural_state_history)[-30:]
            unique = len(set(recent))
            od = safe_prob(max(0.0, 1.0 - unique / 9.0))
            if od > 0.6:
                notes.append("low_state_diversity")
        # narrative_fixation: long single-state runs
        nf = 0.0
        if len(self._structural_state_history) >= 10:
            recent = list(self._structural_state_history)[-10:]
            if len(set(recent)) == 1:
                nf = 0.7; notes.append("single_state_fixation")

        return DriftReport(
            calibration_decay=cd,
            memory_contamination=mc,
            overfitting_drift=od,
            narrative_fixation=nf,
            notes=notes,
        )
