"""ConfidenceState — orchestrator-aggregated global confidence (Appendix F + O)."""

from __future__ import annotations

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat


class ConfidenceState(MSPISSchema):
    """Aggregated confidence with penalty traceability.

    The single authority for confidence is the orchestrator. Modules submit
    their per-module confidence; the orchestrator combines them via weighted
    geometric mean then applies the multiplicative exponential penalty from
    Appendix O.
    """

    raw_geometric_mean: UnitFloat
    instability_penalty: UnitFloat = Field(description="exp(-λ1 * instability)")
    contradiction_penalty: UnitFloat = Field(description="exp(-λ2 * contradiction)")
    entropy_penalty: UnitFloat = Field(description="exp(-λ3 * entropy)")
    global_confidence: UnitFloat
    contributors: tuple[str, ...] = Field(default_factory=tuple)
    lambda1: float = Field(ge=0.0)
    lambda2: float = Field(ge=0.0)
    lambda3: float = Field(ge=0.0)
