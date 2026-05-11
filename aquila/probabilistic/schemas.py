from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    weight: float = 1.0
    likelihood: float
    source_event_id: str | None = None


class PosteriorBelief(BaseModel):
    model_config = ConfigDict(frozen=True)
    hypothesis: str
    prior: float
    posterior: float
    evidence: list[Evidence] = Field(default_factory=list)
