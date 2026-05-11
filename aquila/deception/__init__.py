"""Layer 6 — Deception Intelligence Layer.

DIAGNOSES deception probability. Does NOT produce trade signals, directions,
entries, targets, stops, or actions. Enforced by `safety.kernel` on every
emission of this layer.

Sub-modules:
- schemas.py    : DeceptionReport, TrapSignature, LureClassification, NarrativeDivergence
- interfaces.py : DeceptionService, TrapDetector, LureClassifier
- traps.py      : bull/bear trap detection
- lure.py       : liquidity-lure analysis
- narrative.py  : narrative divergence scoring
- signatures.py : engineered manipulation signature library
- safety.py     : enforces "no trade signals" invariants on layer output
- engine.py     : DeceptionIntelligenceLayer
"""

from aquila.deception.engine import DeceptionIntelligenceLayer
from aquila.deception.schemas import (
    DeceptionKind,
    DeceptionReport,
    LureClassification,
    NarrativeDivergence,
    TrapSignature,
)

__all__ = [
    "DeceptionIntelligenceLayer",
    "DeceptionKind",
    "DeceptionReport",
    "LureClassification",
    "NarrativeDivergence",
    "TrapSignature",
]
