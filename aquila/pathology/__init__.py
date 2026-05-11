"""Layer 3 — Pathology & Contradiction.

Detects structural pathologies (incongruences, breakdowns, exhaustion,
absorption-on-displacement, etc.) and the *contradictions* between
co-occurring features. Outputs a contradiction-weighted confidence.
"""

from aquila.pathology.schemas import (
    Contradiction,
    PathologyKind,
    PathologyReport,
    PathologySignature,
)
from aquila.pathology.service import PathologyContradictionLayer

__all__ = [
    "Contradiction",
    "PathologyKind",
    "PathologyReport",
    "PathologySignature",
    "PathologyContradictionLayer",
]
