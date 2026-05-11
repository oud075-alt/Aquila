from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Symbol


class IntermarketRelation(BaseModel):
    model_config = ConfigDict(frozen=True)
    a: Symbol
    b: Symbol
    score: float
    kind: str
    rationale: str = ""


class IntermarketReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    relations: list[IntermarketRelation] = Field(default_factory=list)
    contradictions: list[IntermarketRelation] = Field(default_factory=list)
    liquidity_migrations: list[IntermarketRelation] = Field(default_factory=list)
    regime_contagion: list[IntermarketRelation] = Field(default_factory=list)
