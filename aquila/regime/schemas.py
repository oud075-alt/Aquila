from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RegimeKind(str, Enum):
    LOW_VOL = "low_vol"
    NORMAL_VOL = "normal_vol"
    HIGH_VOL = "high_vol"
    THIN_LIQUIDITY = "thin_liquidity"
    DEEP_LIQUIDITY = "deep_liquidity"
    LOW_PARTICIPATION = "low_participation"
    HIGH_PARTICIPATION = "high_participation"
    UNSTABLE = "unstable"


class RegimeState(BaseModel):
    model_config = ConfigDict(frozen=True)
    volatility: RegimeKind = RegimeKind.NORMAL_VOL
    liquidity: RegimeKind = RegimeKind.DEEP_LIQUIDITY
    participation: RegimeKind = RegimeKind.HIGH_PARTICIPATION
    instability: float = 0.0


class RegimeTransition(BaseModel):
    model_config = ConfigDict(frozen=True)
    from_state: RegimeState
    to_state: RegimeState
    probability: float
    rationale: str = ""


class RegimeMutationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    current: RegimeState
    mutations: list[str] = Field(default_factory=list)
    transitions: list[RegimeTransition] = Field(default_factory=list)
    instability_score: float = 0.0
    calibration_delta: float = 0.0
