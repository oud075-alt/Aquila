"""Layer 8 — Meta-Cognition Layer.

The system evaluates itself. Inspects all upstream layer outputs and
publishes:
- model uncertainty score
- self-consistency assessment
- low-visibility detection
- recursive confidence validation (bounded to depth=1 to satisfy
  audit gap #50: bounded reflexivity)
"""

from aquila.meta.engine import MetaCognitionLayer
from aquila.meta.schemas import (
    CognitiveConfidenceEdge,
    CognitiveConfidenceGraph,
    MetaCognitiveReport,
    MetaSignal,
    SelfConsistencyResult,
    UncertaintyModel,
)

__all__ = [
    "MetaCognitionLayer",
    "CognitiveConfidenceEdge",
    "CognitiveConfidenceGraph",
    "MetaCognitiveReport",
    "MetaSignal",
    "SelfConsistencyResult",
    "UncertaintyModel",
]
