"""ContradictionReport — output of the contradiction engine (Phase 0D)."""

from __future__ import annotations

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.enums import ContradictionPolicy


class ContradictionFinding(MSPISSchema):
    """A single fired contradiction rule."""

    pair_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=256)
    policy: ContradictionPolicy
    severity: UnitFloat


class ContradictionReport(MSPISSchema):
    """Aggregated contradiction state for a single diagnosis."""

    findings: tuple[ContradictionFinding, ...] = Field(default_factory=tuple)
    contradiction_score: UnitFloat
    invalid_count: int = Field(default=0, ge=0)
    unstable_count: int = Field(default=0, ge=0)
    critical_count: int = Field(default=0, ge=0)
    validation_failed: bool = False
    defensive_override: bool = False

    @property
    def is_clean(self) -> bool:
        return not self.findings
