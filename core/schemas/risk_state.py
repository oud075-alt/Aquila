"""RiskState — Phase 4 systemic risk envelope."""

from __future__ import annotations

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.enums import RiskBand


class RiskState(MSPISSchema):
    """Phase 4 risk intelligence output."""

    risk_band: RiskBand
    systemic_risk_score: UnitFloat
    collapse_probability: UnitFloat
    instability_probability: UnitFloat
    defensive_risk_modifier: UnitFloat
    confidence_decay: UnitFloat
    participation_safety: UnitFloat
    fragility_index: UnitFloat
    reasoning: tuple[str, ...] = Field(default_factory=tuple)
