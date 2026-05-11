"""Phase 0E — Orchestrator substrate.

The orchestrator is the SINGLE authoritative intelligence coordinator
(ORCHESTRATOR AUTHORITY LOCK). All sequencing, state propagation,
confidence aggregation, context synchronization, and diagnosis merging
flow through these modules.
"""

from core.orchestrator.context_manager import ContextManager
from core.orchestrator.diagnosis_coordinator import DiagnosisCoordinator
from core.orchestrator.pipeline_executor import PipelineExecutor
from core.orchestrator.regime_classifier import RegimeClassifier
from core.orchestrator.state_bus import StateBus

__all__ = [
    "ContextManager",
    "DiagnosisCoordinator",
    "PipelineExecutor",
    "RegimeClassifier",
    "StateBus",
]
