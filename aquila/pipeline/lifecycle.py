from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import LayerName


class LifecyclePhase(str, Enum):
    INGEST = "ingest"
    PRIMITIVES = "primitives"
    STRUCTURAL = "structural"
    PATHOLOGY = "pathology"
    MEMORY = "memory"
    TEMPORAL = "temporal"
    DECEPTION = "deception"
    REGIME = "regime"
    META = "meta"
    NARRATIVE = "narrative"
    AUDIT = "audit"
    DONE = "done"


class EventLifecycle(BaseModel):
    model_config = ConfigDict(frozen=True)
    correlation_id: str
    phases_completed: list[LifecyclePhase] = Field(default_factory=list)
    phases_skipped: list[LifecyclePhase] = Field(default_factory=list)
    layer_confidences: dict[LayerName, float] = Field(default_factory=dict)
