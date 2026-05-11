"""Confidence scoring — pathology-level confidence aggregation."""

from __future__ import annotations

from aquila.core.confidence import ConfidenceCalculus
from aquila.pathology.schemas import Contradiction, PathologySignature


def pathology_confidence(
    sigs: list[PathologySignature], contras: list[Contradiction]
) -> float:
    sig_conf = ConfidenceCalculus.combine_independent([s.score for s in sigs])
    contra_score = ConfidenceCalculus.combine_independent([c.score for c in contras])
    return ConfidenceCalculus.contradiction_penalty(sig_conf, contra_score)
