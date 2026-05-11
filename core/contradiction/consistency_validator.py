"""Consistency validator — turns matrix findings into a ContradictionReport.

Applies the policy action semantics defined in Appendix X and ADR-0003:

    INVALID  → validation_failed=True, confidence→0, defensive_state=True
    UNSTABLE → confidence *= 0.5, contradiction_score = max(score, 0.7)
    CRITICAL → defensive_override=True, escalation_risk=max(risk, 0.85),
               participation_safety=min(safety, 0.15)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.contradiction.contradiction_matrix import ContradictionContext, ContradictionMatrix
from core.schemas.contradiction_report import ContradictionFinding, ContradictionReport
from core.schemas.enums import ContradictionPolicy, SourceMode, Timeframe

UNSTABLE_CONFIDENCE_FACTOR: float = 0.5
UNSTABLE_SCORE_FLOOR: float = 0.70
CRITICAL_ESCALATION_FLOOR: float = 0.85
CRITICAL_PARTICIPATION_CEILING: float = 0.15


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validator output, consumed by the orchestrator."""

    report: ContradictionReport
    confidence_multiplier: float
    escalation_floor: float
    participation_ceiling: float
    defensive_override: bool
    validation_failed: bool


class ConsistencyValidator:
    """Single authority for converting matrix findings into a structured report."""

    def __init__(self, matrix: ContradictionMatrix | None = None) -> None:
        self.matrix = matrix or ContradictionMatrix()

    def validate(
        self,
        *,
        context: ContradictionContext,
        timestamp: datetime,
        timeframe: Timeframe,
        source: SourceMode,
        base_confidence: float,
    ) -> ValidationResult:
        triggered = self.matrix.evaluate(context)

        invalid_count = 0
        unstable_count = 0
        critical_count = 0

        findings: list[ContradictionFinding] = []
        max_severity: float = 0.0

        for rule, severity in triggered:
            findings.append(
                ContradictionFinding(
                    timestamp=timestamp,
                    timeframe=timeframe,
                    source=source,
                    confidence=base_confidence,
                    pair_id=rule.id,
                    description=rule.description,
                    policy=rule.policy,
                    severity=severity,
                )
            )
            if rule.policy is ContradictionPolicy.INVALID:
                invalid_count += 1
            elif rule.policy is ContradictionPolicy.UNSTABLE:
                unstable_count += 1
            elif rule.policy is ContradictionPolicy.CRITICAL:
                critical_count += 1
            max_severity = max(max_severity, severity)

        score = self._compute_contradiction_score(invalid_count, unstable_count, critical_count, max_severity)

        validation_failed = invalid_count > 0
        defensive_override = critical_count > 0 or invalid_count > 0

        if validation_failed:
            confidence_multiplier = 0.0
            score = max(score, 0.99)
        elif unstable_count > 0:
            confidence_multiplier = UNSTABLE_CONFIDENCE_FACTOR
            score = max(score, UNSTABLE_SCORE_FLOOR)
        else:
            confidence_multiplier = 1.0

        escalation_floor = CRITICAL_ESCALATION_FLOOR if critical_count > 0 else 0.0
        participation_ceiling = CRITICAL_PARTICIPATION_CEILING if critical_count > 0 else 1.0

        report = ContradictionReport(
            timestamp=timestamp,
            timeframe=timeframe,
            source=source,
            confidence=base_confidence * confidence_multiplier,
            findings=tuple(findings),
            contradiction_score=min(1.0, max(0.0, score)),
            invalid_count=invalid_count,
            unstable_count=unstable_count,
            critical_count=critical_count,
            validation_failed=validation_failed,
            defensive_override=defensive_override,
        )

        return ValidationResult(
            report=report,
            confidence_multiplier=confidence_multiplier,
            escalation_floor=escalation_floor,
            participation_ceiling=participation_ceiling,
            defensive_override=defensive_override,
            validation_failed=validation_failed,
        )

    @staticmethod
    def _compute_contradiction_score(
        invalid: int, unstable: int, critical: int, max_sev: float
    ) -> float:
        if invalid == 0 and unstable == 0 and critical == 0:
            return 0.0
        weighted = (1.0 * invalid + 0.7 * critical + 0.4 * unstable) / 3.0
        bounded = 1.0 - (1.0 / (1.0 + weighted))
        return min(1.0, max(bounded, max_sev * 0.5))
