"""TimeframeContext — Phase 2 multi-timeframe fusion outputs (Appendix C)."""

from __future__ import annotations

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.enums import Regime, StructuralState, Timeframe


class TimeframeSnapshot(MSPISSchema):
    """Per-timeframe snapshot fed into context fusion."""

    structural_state: StructuralState
    regime: Regime
    instability_score: UnitFloat
    structural_health: UnitFloat
    is_stale: bool = False


class TimeframeContext(MSPISSchema):
    """Phase 2 fusion output across all mandatory timeframes."""

    snapshots: tuple[TimeframeSnapshot, ...] = Field(min_length=1, max_length=5)
    context_alignment_score: UnitFloat
    macro_bias: Regime
    local_bias: Regime
    timeframe_conflict_score: UnitFloat
    structural_consensus: UnitFloat
    escalation_alignment: UnitFloat
    higher_timeframe_authority: Timeframe
    reasoning: tuple[str, ...] = Field(default_factory=tuple)
