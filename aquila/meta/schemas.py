from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import LayerName


class UncertaintyModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    epistemic: float = 0.0
    aleatoric: float = 0.0
    visibility_penalty: float = 0.0
    contradiction_penalty: float = 0.0
    @property
    def total(self) -> float:
        return min(1.0, self.epistemic + self.aleatoric + self.visibility_penalty + self.contradiction_penalty)


class CognitiveConfidenceEdge(BaseModel):
    model_config = ConfigDict(frozen=True)
    layer: LayerName
    confidence: float
    visibility: str


class CognitiveConfidenceGraph(BaseModel):
    model_config = ConfigDict(frozen=True)
    edges: list[CognitiveConfidenceEdge] = Field(default_factory=list)


class SelfConsistencyResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    consistent: bool
    conflicts: list[str] = Field(default_factory=list)


class MetaSignal(BaseModel):
    """Feedback emitted to the next cycle. Pure data, no actions."""

    model_config = ConfigDict(frozen=True)
    elevated_uncertainty: bool = False
    cap_downstream_confidence: float | None = None
    notes: list[str] = Field(default_factory=list)


class MetaCognitiveReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    uncertainty: UncertaintyModel
    confidence_graph: CognitiveConfidenceGraph
    self_consistency: SelfConsistencyResult
    low_visibility_layers: list[LayerName] = Field(default_factory=list)
    cognitive_health: float = 0.0
    meta_signal: MetaSignal = MetaSignal()
