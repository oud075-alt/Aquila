"""MSPIS — Market Structural Pathology Intelligence System.

The :mod:`brain` package houses the entire intelligence engine. It is
organised into clearly separated cognitive layers:

* :mod:`brain.sensory`       — market data ingestion
* :mod:`brain.expectation`   — healthy market physiology models
* :mod:`brain.pathology`     — anomaly + structural disease models
* :mod:`brain.intelligence`  — contradiction → diagnosis → escalation
* :mod:`brain.memory`        — vector / pattern / failure / adaptive memory
* :mod:`brain.gpt`           — GPT reasoning bridge (interpretation only)
* :mod:`brain.execution`     — alerts, reports, projections (no orders)

The orchestrator (:mod:`brain.orchestrator`) is the single entry point that
ties the layers together according to the mandatory intelligence flow.
"""

from .schemas import (
    StandardizedDiagnosis,
    MarketSnapshot,
    Candle,
    PathologyScores,
    ContradictionScores,
    ExpectationProfile,
    ActualBehaviorProfile,
    StateTransition,
    DiagnosisLabel,
    SeverityLevel,
)

__all__ = [
    "StandardizedDiagnosis",
    "MarketSnapshot",
    "Candle",
    "PathologyScores",
    "ContradictionScores",
    "ExpectationProfile",
    "ActualBehaviorProfile",
    "StateTransition",
    "DiagnosisLabel",
    "SeverityLevel",
]

__version__ = "1.0.0"
