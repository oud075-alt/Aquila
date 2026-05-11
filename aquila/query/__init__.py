"""Cognitive query interface — read-model projections over the event store."""

from aquila.query.engine import CognitiveQueryEngine
from aquila.query.projections import Projection
from aquila.query.schemas import (
    CausalTraceQuery,
    CausalTraceResult,
    PathologyHistoryQuery,
    PathologyHistoryResult,
    StructuralStateQuery,
    StructuralStateResult,
    TemporalContradictionQuery,
    TemporalContradictionResult,
)

__all__ = [
    "CognitiveQueryEngine",
    "Projection",
    "CausalTraceQuery",
    "CausalTraceResult",
    "PathologyHistoryQuery",
    "PathologyHistoryResult",
    "StructuralStateQuery",
    "StructuralStateResult",
    "TemporalContradictionQuery",
    "TemporalContradictionResult",
]
