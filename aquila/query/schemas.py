from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Symbol


class StructuralStateQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: Symbol
    last_n: int = 50


class StructuralStateResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    states: list[str] = Field(default_factory=list)


class PathologyHistoryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: Symbol
    last_n: int = 50


class PathologyHistoryResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    pathology_scores: list[float] = Field(default_factory=list)
    contradiction_scores: list[float] = Field(default_factory=list)


class TemporalContradictionQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: Symbol


class TemporalContradictionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    edges: list[dict] = Field(default_factory=list)


class CausalTraceQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    correlation_id: str


class CausalTraceResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    nodes: list[str] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
