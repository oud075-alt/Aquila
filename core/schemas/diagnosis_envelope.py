"""DiagnosisEnvelope — the unified output of the MSPIS orchestrator.

Every API response, persistence row, and downstream consumer reads this object.
Every required field listed in the STANDARDIZED OUTPUT REQUIREMENT is present.

The envelope is the SINGLE structural intelligence object MSPIS emits.
"""

from __future__ import annotations

from pydantic import Field

from core.schemas._base import MSPISSchema, UnitFloat
from core.schemas.confidence_state import ConfidenceState
from core.schemas.contradiction_report import ContradictionReport
from core.schemas.enums import StrategyEnvironment
from core.schemas.pathology_report import PathologyReport
from core.schemas.regime_state import RegimeState
from core.schemas.risk_state import RiskState
from core.schemas.timeframe_context import TimeframeContext


class DiagnosisReasoning(MSPISSchema):
    """Explainability payload — narrates WHY the diagnosis emerged."""

    summary: str
    drivers: tuple[str, ...] = Field(default_factory=tuple)
    invalid_pairs: tuple[str, ...] = Field(default_factory=tuple)
    suppressors: tuple[str, ...] = Field(default_factory=tuple)


class DecisionPayload(MSPISSchema):
    """Phase 1 deterministic decision payload (NOT a trading signal)."""

    action: str = Field(min_length=1, max_length=64)
    risk_mode: str = Field(min_length=1, max_length=64)
    strategy_bias: str = Field(min_length=1, max_length=64)
    avoid_conditions: tuple[str, ...] = Field(default_factory=tuple)
    structural_bias: str = Field(min_length=1, max_length=64)
    defensive_state: bool = False
    structural_environment: StrategyEnvironment = StrategyEnvironment.UNSTABLE
    recommended_behavior: str = Field(min_length=1, max_length=128)
    execution_safety: UnitFloat = 0.0
    participation_bias: UnitFloat = 0.0
    avoidance_bias: UnitFloat = 0.0


class DiagnosisEnvelope(MSPISSchema):
    """The unified MSPIS diagnosis emitted by the orchestrator."""

    symbol: str = Field(default="BTCUSDT")
    market_state_hash: str = Field(min_length=8, max_length=128)
    structural_health: UnitFloat
    escalation_risk: UnitFloat
    defensive_state: bool

    pathology: PathologyReport
    contradiction: ContradictionReport
    regime: RegimeState
    risk: RiskState
    confidence_state: ConfidenceState
    timeframe_context: TimeframeContext | None = None
    decision: DecisionPayload

    reasoning: DiagnosisReasoning
    validation_failed: bool = False
