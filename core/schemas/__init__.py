"""Phase 0A — Versioned schema contracts consumed by every downstream module.

Every schema in this package:
    - is Pydantic v2
    - is frozen (immutable) once constructed
    - forbids extra fields
    - carries schema_version, timestamp (UTC tz-aware), timeframe, source, confidence
    - is the SINGLE allowed representation of its state
"""

from core.schemas.confidence_state import ConfidenceState
from core.schemas.contradiction_report import (
    ContradictionFinding,
    ContradictionReport,
)
from core.schemas.diagnosis_envelope import DiagnosisEnvelope
from core.schemas.enums import (
    ContradictionPolicy,
    Regime,
    SourceMode,
    StructuralState,
    Timeframe,
)
from core.schemas.market_state import MarketBar, MarketState
from core.schemas.pathology_report import PathologyReport, PathologyScores
from core.schemas.regime_state import RegimeState
from core.schemas.risk_state import RiskState
from core.schemas.timeframe_context import TimeframeContext, TimeframeSnapshot

__all__ = [
    "ConfidenceState",
    "ContradictionFinding",
    "ContradictionPolicy",
    "ContradictionReport",
    "DiagnosisEnvelope",
    "MarketBar",
    "MarketState",
    "PathologyReport",
    "PathologyScores",
    "Regime",
    "RegimeState",
    "RiskState",
    "SchemaVersion",
    "SourceMode",
    "StructuralState",
    "Timeframe",
    "TimeframeContext",
    "TimeframeSnapshot",
]

SchemaVersion: str = "0.1.0"
