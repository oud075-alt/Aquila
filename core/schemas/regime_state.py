"""RegimeState — closed-enum regime classification (Appendix B)."""

from __future__ import annotations

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.enums import Regime


class RegimeState(MSPISSchema):
    """Current regime classification with persistence statistics."""

    regime: Regime
    regime_confidence: UnitFloat
    regime_persistence_bars: int = Field(ge=0)
    transition_pressure: UnitFloat
    previous_regime: Regime | None = None
    reasoning: tuple[str, ...] = Field(default_factory=tuple)
