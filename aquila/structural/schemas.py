from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StructuralState(str, Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    EXPANSION = "expansion"
    COMPRESSION = "compression"
    EXHAUSTION = "exhaustion"
    ABSORPTION = "absorption"
    DISPLACEMENT = "displacement"
    UNKNOWN = "unknown"


class StructuralFeature(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    value: float
    weight: float = 1.0


class StructuralDiagnosis(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: StructuralState
    secondary_state: StructuralState | None = None
    features: list[StructuralFeature] = Field(default_factory=list)
    score: float = 0.0
    notes: list[str] = Field(default_factory=list)
