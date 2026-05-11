from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CausalEdgeKind(str, Enum):
    CORRELATION = "correlation"
    STRUCTURAL_DEPENDENCY = "structural_dependency"
    CAUSAL_ESCALATION = "causal_escalation"
    TEMPORAL_CAUSAL = "temporal_causal"


class CausalEdge(BaseModel):
    model_config = ConfigDict(frozen=True)
    from_event: str
    to_event: str
    kind: CausalEdgeKind
    weight: float = 1.0
    rationale: str = ""


class CausalGraph(BaseModel):
    model_config = ConfigDict(frozen=True)
    edges: list[CausalEdge] = Field(default_factory=list)
