"""FastAPI dependency-injection holder for the orchestrator + governance objects.

A single process holds one `AppState`. Multi-process / distributed
deployments swap this with a transport-backed singleton.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aquila.governance.assumptions import AssumptionRegistry
from aquila.governance.eventstore import EventStore
from aquila.governance.snapshots import SnapshotManager
from aquila.intermarket import IntermarketCognition
from aquila.narrative import NarrativeExplainer
from aquila.ontology.registry import OntologyRegistry
from aquila.pipeline import CognitiveOrchestrator
from aquila.protocols.compatibility import ProtocolCompatibilityMatrix
from aquila.query.engine import CognitiveQueryEngine
from aquila.safety import SafetyKernel
from aquila.validation.suite import ValidationSuite
from aquila.core.types import LayerName


@dataclass
class AppState:
    orchestrator: CognitiveOrchestrator = field(default_factory=CognitiveOrchestrator)
    event_store: EventStore = field(default_factory=EventStore)
    ontology: OntologyRegistry = field(default_factory=OntologyRegistry)
    safety: SafetyKernel = field(default_factory=SafetyKernel)
    protocols: ProtocolCompatibilityMatrix = field(default_factory=ProtocolCompatibilityMatrix)
    assumptions: AssumptionRegistry = field(default_factory=AssumptionRegistry)
    snapshots: SnapshotManager = field(default_factory=SnapshotManager)
    intermarket: IntermarketCognition = field(default_factory=IntermarketCognition)
    narrative: NarrativeExplainer = field(default_factory=NarrativeExplainer)
    latest_by_corr: dict = field(default_factory=dict)

    def make_query_engine(self) -> CognitiveQueryEngine:
        return CognitiveQueryEngine(self.event_store, self.latest_by_corr)

    def make_validation_suite(self) -> ValidationSuite:
        return ValidationSuite(
            self.orchestrator.audit, self.ontology, self.safety,
            self.protocols, self.assumptions,
        )

    def record(self, outputs: dict[LayerName, "LayerOutput"]) -> None:  # type: ignore[name-defined]
        for o in outputs.values():
            self.event_store.append(o)
        if outputs:
            corr = next(iter(outputs.values())).correlation_id
            self.latest_by_corr[corr] = dict(outputs)
            self.intermarket.observe(next(iter(outputs.values())).symbol, outputs)


_state: AppState | None = None


def state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state


def reset_state() -> None:
    global _state
    _state = AppState()
