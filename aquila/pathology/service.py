from __future__ import annotations

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.types import LayerName, Severity
from aquila.pathology.confidence import pathology_confidence
from aquila.pathology.contradiction import detect_contradictions
from aquila.pathology.interfaces import PathologyService
from aquila.pathology.schemas import PathologyKind, PathologyReport, PathologySignature
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis, StructuralState


def _severity(score: float) -> Severity:
    if score >= 0.8:
        return Severity.CRITICAL
    if score >= 0.6:
        return Severity.HIGH
    if score >= 0.4:
        return Severity.MODERATE
    if score >= 0.2:
        return Severity.LOW
    return Severity.NIL


class PathologyContradictionLayer(PathologyService):
    layer_name = LayerName.PATHOLOGY

    def process(
        self, payload: StructuralDiagnosis, ctx: LayerContext
    ) -> LayerOutput[PathologyReport]:
        prim_out = ctx.upstream_outputs.get(LayerName.PRIMITIVES)
        snap: PrimitiveSnapshot | None = prim_out.payload if prim_out else None  # type: ignore[assignment]

        sigs: list[PathologySignature] = []

        if snap is not None:
            if payload.state in (StructuralState.TREND_UP, StructuralState.TREND_DOWN):
                if max(snap.upper_wick_ratio, snap.lower_wick_ratio) > 0.55:
                    s = 0.6
                    sigs.append(PathologySignature(
                        kind=PathologyKind.EXHAUSTION_ON_TREND,
                        severity=_severity(s), score=s,
                        evidence=["wick_dominance"],
                    ))

            if payload.state == StructuralState.DISPLACEMENT and snap.volume_z > 1.5 and snap.body_ratio < 0.5:
                s = 0.7
                sigs.append(PathologySignature(
                    kind=PathologyKind.ABSORPTION_ON_DISPLACEMENT,
                    severity=_severity(s), score=s,
                    evidence=["high_volume_low_body"],
                ))

            if payload.state == StructuralState.COMPRESSION and snap.realized_vol > 0.02:
                s = 0.55
                sigs.append(PathologySignature(
                    kind=PathologyKind.COMPRESSION_BREAKDOWN,
                    severity=_severity(s), score=s,
                    evidence=["rvol_breakout"],
                ))

            if payload.state == StructuralState.EXPANSION and snap.volume_z < -0.3:
                s = 0.5
                sigs.append(PathologySignature(
                    kind=PathologyKind.EXPANSION_WITHOUT_VOLUME,
                    severity=_severity(s), score=s,
                    evidence=["volume_thin"],
                ))

        contras = detect_contradictions(payload, snap)

        agg_pathology = pathology_confidence(sigs, [])
        agg_contra = sum(c.score for c in contras) / max(1, len(contras)) if contras else 0.0

        report = PathologyReport(
            signatures=sigs,
            contradictions=contras,
            aggregate_pathology_score=agg_pathology,
            aggregate_contradiction_score=agg_contra,
        )
        confidence = pathology_confidence(sigs, contras)
        return self.wrap(payload=report, ctx=ctx, confidence=confidence)
