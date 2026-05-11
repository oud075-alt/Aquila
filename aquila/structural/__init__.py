"""Layer 2 — Structural Diagnosis.

Classifies the current bar/window into a structural state taxonomy:
trend, range, expansion, compression, exhaustion, absorption, displacement.
This layer is the bridge between numeric primitives and pathology cognition.
"""

from aquila.structural.schemas import (
    StructuralDiagnosis,
    StructuralFeature,
    StructuralState,
)
from aquila.structural.service import StructuralDiagnosisLayer

__all__ = [
    "StructuralDiagnosis",
    "StructuralFeature",
    "StructuralState",
    "StructuralDiagnosisLayer",
]
