"""MSPIS brain layer — Phase 1-5 structural cognition modules.

Each brain module is wired into the orchestrator via the hook protocol
defined in `core.orchestrator.pipeline_executor`. Brain modules are
forbidden from emitting trade signals (Appendix I + Y).
"""

from brain.adaptive_learning import AdaptiveLearningEngine
from brain.context_fusion import ContextFusionEngine
from brain.decision_engine import DecisionEngine
from brain.risk_intelligence import RiskIntelligenceEngine
from brain.strategy_router import StrategyRouter

__all__ = [
    "AdaptiveLearningEngine",
    "ContextFusionEngine",
    "DecisionEngine",
    "RiskIntelligenceEngine",
    "StrategyRouter",
]
