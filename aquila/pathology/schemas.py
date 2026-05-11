from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Severity


class PathologyKind(str, Enum):
    EXHAUSTION_ON_TREND = "exhaustion_on_trend"
    ABSORPTION_ON_DISPLACEMENT = "absorption_on_displacement"
    COMPRESSION_BREAKDOWN = "compression_breakdown"
    EXPANSION_WITHOUT_VOLUME = "expansion_without_volume"
    DISPLACEMENT_WITHOUT_FOLLOW_THROUGH = "displacement_without_follow_through"
    VOLATILITY_DECOUPLE = "volatility_decouple"


class Contradiction(BaseModel):
    model_config = ConfigDict(frozen=True)
    a: str
    b: str
    score: float
    rationale: str = ""


class PathologySignature(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: PathologyKind
    severity: Severity
    score: float
    evidence: list[str] = Field(default_factory=list)


class PathologyReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    signatures: list[PathologySignature] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    aggregate_pathology_score: float = 0.0
    aggregate_contradiction_score: float = 0.0
