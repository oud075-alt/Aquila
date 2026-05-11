from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Severity


class DeceptionKind(str, Enum):
    BULL_TRAP = "bull_trap"
    BEAR_TRAP = "bear_trap"
    LIQUIDITY_LURE = "liquidity_lure"
    FALSE_CONTINUATION = "false_continuation"
    NARRATIVE_DIVERGENCE = "narrative_divergence"
    ABSORPTION_DECEPTION = "absorption_deception"


class TrapSignature(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: DeceptionKind
    probability: float
    severity: Severity
    rationale: str = ""


class LureClassification(BaseModel):
    model_config = ConfigDict(frozen=True)
    lure_type: str
    probability: float
    target_zone_hint: str | None = None


class NarrativeDivergence(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: float
    description: str = ""


class DeceptionReport(BaseModel):
    """Diagnostic-only payload. By contract this schema MUST NOT contain
    any fields that resemble trade instructions. Forbidden field names are
    enforced by `safety.kernel.FORBIDDEN_SIGNAL_FIELDS`.
    """

    model_config = ConfigDict(frozen=True)
    deception_probability: float = 0.0
    signatures: list[TrapSignature] = Field(default_factory=list)
    lures: list[LureClassification] = Field(default_factory=list)
    narrative: NarrativeDivergence | None = None
    notes: list[str] = Field(default_factory=list)
