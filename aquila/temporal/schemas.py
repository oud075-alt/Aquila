from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.time import Timeframe
from aquila.structural.schemas import StructuralState


class TimeframeState(BaseModel):
    model_config = ConfigDict(frozen=True)
    timeframe: Timeframe
    state: StructuralState
    secondary: StructuralState | None = None
    confidence: float = 0.0


class HierarchyWeights(BaseModel):
    model_config = ConfigDict(frozen=True)
    weights: dict[Timeframe, float] = Field(default_factory=lambda: {
        Timeframe.M1: 0.05,
        Timeframe.M5: 0.10,
        Timeframe.M15: 0.15,
        Timeframe.H1: 0.20,
        Timeframe.H4: 0.25,
        Timeframe.D1: 0.25,
    })

    def weight(self, tf: Timeframe) -> float:
        return self.weights.get(tf, 0.0)


class TemporalConflict(BaseModel):
    model_config = ConfigDict(frozen=True)
    higher: Timeframe
    lower: Timeframe
    higher_state: StructuralState
    lower_state: StructuralState
    score: float
    rationale: str = ""


class TemporalConflictGraph(BaseModel):
    model_config = ConfigDict(frozen=True)
    edges: list[TemporalConflict] = Field(default_factory=list)

    @property
    def aggregate_conflict(self) -> float:
        if not self.edges:
            return 0.0
        return sum(e.score for e in self.edges) / len(self.edges)


class TemporalCognition(BaseModel):
    model_config = ConfigDict(frozen=True)
    states: list[TimeframeState]
    fused_state: StructuralState
    alignment_score: float
    conflict_graph: TemporalConflictGraph
    weights: HierarchyWeights
