from __future__ import annotations

from aquila.attention import AttentionAllocator
from aquila.causal import LineageGraph
from aquila.drift import DriftMonitor
from aquila.failure.detector import FailureStateDetector
from aquila.failure.schemas import FailureState
from aquila.governance import AssumptionRegistry, CognitionExporter, EventStore, SnapshotManager
from aquila.intermarket import IntermarketCognition
from aquila.narrative import NarrativeExplainer
from aquila.observability.audit import AuditLog
from aquila.ontology.registry import OntologyRegistry
from aquila.physics import StateTransitionPhysics
from aquila.probabilistic import BayesianReasoner, Evidence
from aquila.protocols.compatibility import ProtocolCompatibilityMatrix
from aquila.query.engine import CognitiveQueryEngine
from aquila.safety import SafetyKernel
from aquila.security import IntegrityValidator
from aquila.simulation import SimulationEngine
from aquila.structural.schemas import StructuralState
from aquila.validation.suite import ValidationSuite


def test_lineage_graph_builds_for_pipeline_outputs(orchestrator, symbol, synthetic_bars):
    last = {}
    for b in synthetic_bars[:5]:
        last = orchestrator.run_tick(symbol, b)
    graph = LineageGraph().build(last)
    assert len(graph.edges) > 0


def test_event_store_and_snapshots(orchestrator, symbol, synthetic_bars):
    es = EventStore()
    last = {}
    for b in synthetic_bars[:3]:
        last = orchestrator.run_tick(symbol, b)
        for o in last.values():
            es.append(o)
    assert len(es) > 0
    snap = SnapshotManager().capture(list(es.stream()))
    assert snap.last_sequence == len(es) - 1


def test_export_round_trip(orchestrator, symbol, synthetic_bars):
    last = orchestrator.run_tick(symbol, synthetic_bars[0])
    blob = CognitionExporter().export(last)
    assert "@context" in blob and len(blob["outputs"]) == 8


def test_bayesian_reasoner_updates():
    pb = BayesianReasoner.update(
        "trap_active", prior=0.2,
        evidence=[Evidence(name="wick", likelihood=0.7, weight=2.0)],
    )
    assert 0.0 <= pb.posterior <= 1.0


def test_intermarket_detects_disagreement(orchestrator, synthetic_bars):
    from aquila.core.types import Symbol
    inter = IntermarketCognition()
    for sym in (Symbol("A"), Symbol("B")):
        for b in synthetic_bars[:5]:
            inter.observe(sym, orchestrator.run_tick(sym, b))
    rep = inter.report()
    assert isinstance(rep.relations, list)


def test_attention_allocator(orchestrator, symbol, synthetic_bars):
    last = orchestrator.run_tick(symbol, synthetic_bars[0])
    rep = AttentionAllocator().allocate(last, top_k=3)
    assert len(rep.top) <= 3


def test_drift_monitor_observes(orchestrator, symbol, synthetic_bars):
    monitor = DriftMonitor()
    for b in synthetic_bars[:10]:
        last = orchestrator.run_tick(symbol, b)
        rep = monitor.observe(last)
    assert 0.0 <= rep.composite <= 1.0


def test_failure_detector_normal_path(orchestrator, symbol, synthetic_bars):
    last = orchestrator.run_tick(symbol, synthetic_bars[0])
    rep = FailureStateDetector().detect(last)
    assert isinstance(rep.state, FailureState)


def test_state_transition_physics():
    eng = StateTransitionPhysics()
    eng.observe(StructuralState.TREND_UP)
    eng.observe(StructuralState.TREND_UP)
    rep = eng.observe(StructuralState.RANGE)
    assert rep.last_transition is not None
    assert rep.last_transition.from_state == "trend_up"


def test_narrative_emits_no_signal_fields(orchestrator, symbol, synthetic_bars):
    last = orchestrator.run_tick(symbol, synthetic_bars[0])
    rep = NarrativeExplainer().explain(last)
    blob = rep.model_dump()
    forbidden = {"action", "direction", "entry", "target", "stop", "buy", "sell"}
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                assert k.lower() not in forbidden
                walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(blob)


def test_validation_suite_passes_on_clean_pipeline(orchestrator, symbol, synthetic_bars):
    last = {}
    for b in synthetic_bars[:3]:
        last = orchestrator.run_tick(symbol, b)
    suite = ValidationSuite(
        orchestrator.audit, OntologyRegistry(), SafetyKernel(),
        ProtocolCompatibilityMatrix(), AssumptionRegistry(),
    )
    rep = suite.run(last)
    assert rep.audit_chain_ok
    assert rep.safety_ok
    assert rep.falsifiability_ok


def test_query_engine_returns_structural_history(orchestrator, symbol, synthetic_bars):
    es = EventStore()
    latest: dict = {}
    for b in synthetic_bars[:5]:
        last = orchestrator.run_tick(symbol, b)
        for o in last.values(): es.append(o)
        latest[next(iter(last.values())).correlation_id] = last
    eng = CognitiveQueryEngine(es, latest)
    from aquila.query.schemas import StructuralStateQuery
    res = eng.structural_states(StructuralStateQuery(symbol=symbol, last_n=10))
    assert len(res.states) == 5


def test_simulation_stress(symbol):
    rep = SimulationEngine().stress(symbol, n_cycles=20, volatility_multiplier=4.0)
    assert rep.cycles_run > 0
    assert 0.0 <= rep.max_uncertainty <= 1.0


def test_integrity_validator(orchestrator):
    val = IntegrityValidator(orchestrator.audit, OntologyRegistry(), ProtocolCompatibilityMatrix())
    assert val.verify_audit_chain()
    assert val.verify_ontology()
    assert val.verify_protocol()


def test_audit_log_tamper_detection():
    log = AuditLog()
    from aquila.core.base import LayerOutput
    from aquila.core.types import LayerName, Symbol, utcnow
    from pydantic import BaseModel, ConfigDict
    class P(BaseModel):
        model_config = ConfigDict(frozen=True)
        v: int = 0
    out = LayerOutput(layer=LayerName.PRIMITIVES, symbol=Symbol("X"),
                      timestamp=utcnow(), correlation_id="c", payload=P())
    log.append(out)
    log.append(out)
    assert log.verify()
    log._records[0] = log._records[0].model_copy(update={"confidence": 0.999})
    assert not log.verify()
