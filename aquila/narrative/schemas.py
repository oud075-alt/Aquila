from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NarrativeReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    correlation_id: str
    structural_summary: str
    pathology_summary: str
    temporal_summary: str
    deception_summary: str
    regime_summary: str
    meta_summary: str
    causal_chain: list[str] = Field(default_factory=list)
    confidence_justification: str
    uncertainty_communication: str
