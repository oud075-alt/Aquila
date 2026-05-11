"""Cognitive pipeline orchestration.

DAG:
    [Layer 0 Ingestion]
            |
            v
    Layer 1 Primitives ----+
            |              |
            v              |
    Layer 2 Structural ----+
            |              |
            v              |
    Layer 3 Pathology -----+
            |              |
            +-> Layer 4 Memory ---+
            |                     |
            +-> Layer 5 Temporal  |
            |                     |
            +-> Layer 6 Deception |
            |                     |
            +-> Layer 7 Regime ---+
                                  |
                                  v
                          Layer 8 Meta
"""

from aquila.pipeline.event_bus import EventBus, Subscription
from aquila.pipeline.lifecycle import EventLifecycle, LifecyclePhase
from aquila.pipeline.orchestrator import CognitiveOrchestrator

__all__ = ["EventBus", "Subscription", "EventLifecycle", "LifecyclePhase", "CognitiveOrchestrator"]
