from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Symbol
from aquila.pathology.schemas import PathologyKind


class SyntheticPathologyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: Symbol
    kind: PathologyKind
    intensity: float = 0.5


class CounterfactualResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    ticks: int
    summary: dict = Field(default_factory=dict)


class ScenarioStressResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    scenario_name: str
    cycles_run: int
    max_uncertainty: float
    max_instability: float
