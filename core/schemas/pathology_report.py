"""PathologyReport — aggregated structural pathology scores for one MarketState.

All six primitives plus the aggregate live here. Scores are bounded [0,1] per
Appendix A. The structural state label is the single-valued classifier output.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.enums import StructuralState


class PathologyScores(MSPISSchema):
    """The six pathology primitives (Appendix M) + their aggregate."""

    entropy_instability: UnitFloat
    autocorrelation_breakdown: UnitFloat
    liquidity_imbalance: UnitFloat
    dispersion_shock: UnitFloat
    volatility_disorder: UnitFloat
    continuation_decay: UnitFloat
    aggregate: UnitFloat

    @property
    def vector(self) -> tuple[float, float, float, float, float, float]:
        return (
            self.entropy_instability,
            self.autocorrelation_breakdown,
            self.liquidity_imbalance,
            self.dispersion_shock,
            self.volatility_disorder,
            self.continuation_decay,
        )


WindowInt = Annotated[int, Field(ge=1, le=1024)]


class PathologyReport(MSPISSchema):
    """Pathology diagnosis for a single bar / state / timeframe."""

    scores: PathologyScores
    structural_state: StructuralState
    structural_health: UnitFloat
    instability_score: UnitFloat
    escalation_risk: UnitFloat
    reasoning: tuple[str, ...] = Field(default_factory=tuple)
    primitives_window: WindowInt = 64
