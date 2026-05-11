"""Phase 0D — Contradiction engine substrate (Appendix N + W + X + O)."""

from core.contradiction.confidence_aggregator import (
    LAMBDA_CONTRADICTION,
    LAMBDA_ENTROPY,
    LAMBDA_INSTABILITY,
    ConfidenceAggregator,
    PerModuleConfidence,
)
from core.contradiction.consistency_validator import ConsistencyValidator, ValidationResult
from core.contradiction.contradiction_matrix import (
    ContradictionContext,
    ContradictionMatrix,
    load_default_rules,
)

__all__ = [
    "LAMBDA_CONTRADICTION",
    "LAMBDA_ENTROPY",
    "LAMBDA_INSTABILITY",
    "ConfidenceAggregator",
    "ConsistencyValidator",
    "ContradictionContext",
    "ContradictionMatrix",
    "PerModuleConfidence",
    "ValidationResult",
    "load_default_rules",
]
