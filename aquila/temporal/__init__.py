"""Layer 5 — Temporal Hierarchy Cognition.

Reasons across M1/M5/H1/H4/D1 timeframes:
- alignment scoring (do the timeframes agree?)
- cross-timeframe contradiction
- temporal conflict graph
- state fusion (one consolidated diagnosis across TFs)
- hierarchy weighting (higher TFs weigh more for regime, lower for execution-grade structure)
"""

from aquila.temporal.engine import TemporalHierarchyLayer
from aquila.temporal.schemas import (
    HierarchyWeights,
    TemporalConflict,
    TemporalConflictGraph,
    TemporalCognition,
    TimeframeState,
)

__all__ = [
    "TemporalHierarchyLayer",
    "HierarchyWeights",
    "TemporalConflict",
    "TemporalConflictGraph",
    "TemporalCognition",
    "TimeframeState",
]
