from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import LayerName


class SalienceScore(BaseModel):
    model_config = ConfigDict(frozen=True)
    layer: LayerName
    event_id: str
    salience: float
    reason: str = ""


class AttentionReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    top: list[SalienceScore] = Field(default_factory=list)
