"""Contradiction detector — finds antagonist feature pairs."""

from __future__ import annotations

from aquila.core.numeric import safe_prob
from aquila.pathology.schemas import Contradiction
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis, StructuralState


def detect_contradictions(
    diag: StructuralDiagnosis, snap: PrimitiveSnapshot | None
) -> list[Contradiction]:
    out: list[Contradiction] = []
    if snap is None:
        return out

    if diag.state == StructuralState.EXPANSION and snap.volume_z < -0.3:
        out.append(Contradiction(
            a="expansion", b="volume_thin",
            score=safe_prob(min(1.0, snap.range_pct * 50)),
            rationale="expansion lacks confirming volume",
        ))
    if diag.state == StructuralState.DISPLACEMENT and snap.body_ratio < 0.5:
        out.append(Contradiction(
            a="displacement", b="weak_body", score=0.4,
            rationale="displacement classified but body is small",
        ))
    if diag.state in (StructuralState.TREND_UP, StructuralState.TREND_DOWN) and snap.upper_wick_ratio > 0.6:
        out.append(Contradiction(
            a="trend", b="upper_wick_dominance", score=0.5,
            rationale="trend annotation with rejection wick",
        ))
    if diag.state == StructuralState.COMPRESSION and snap.realized_vol > 0.02:
        out.append(Contradiction(
            a="compression", b="elevated_realized_vol", score=0.6,
            rationale="compression label inconsistent with realized vol",
        ))
    return out
