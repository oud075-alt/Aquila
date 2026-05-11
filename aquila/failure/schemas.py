from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FailureState(str, Enum):
    NORMAL = "normal"
    DEGRADED_COGNITION = "degraded_cognition"
    UNCERTAINTY_OVERFLOW = "uncertainty_overflow"
    CONTRADICTION_SATURATION = "contradiction_saturation"
    LOW_VISIBILITY_LOCKDOWN = "low_visibility_lockdown"
    INSTABILITY_ESCALATION = "instability_escalation"


class FailureStateReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: FailureState = FailureState.NORMAL
    reasons: list[str] = Field(default_factory=list)
    recommend_partial_reasoning: bool = False
