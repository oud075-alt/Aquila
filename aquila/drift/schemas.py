from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DriftReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    calibration_decay: float = 0.0
    memory_contamination: float = 0.0
    overfitting_drift: float = 0.0
    narrative_fixation: float = 0.0
    notes: list[str] = Field(default_factory=list)

    @property
    def composite(self) -> float:
        return min(1.0,
            0.3 * self.calibration_decay
            + 0.3 * self.memory_contamination
            + 0.2 * self.overfitting_drift
            + 0.2 * self.narrative_fixation
        )
