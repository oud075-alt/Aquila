from __future__ import annotations

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.numeric import safe_prob
from aquila.core.types import LayerName
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.interfaces import StructuralDiagnosisService
from aquila.structural.schemas import StructuralDiagnosis, StructuralFeature, StructuralState


class StructuralDiagnosisLayer(StructuralDiagnosisService):
    layer_name = LayerName.STRUCTURAL

    # Thresholds — tunable via config layer in production
    EXPANSION_RANGE_PCT = 0.012
    COMPRESSION_RANGE_PCT = 0.003
    DISPLACEMENT_BODY_RATIO = 0.7
    EXHAUSTION_WICK_RATIO = 0.55
    ABSORPTION_VOL_Z = 1.5

    def process(
        self, payload: PrimitiveSnapshot, ctx: LayerContext
    ) -> LayerOutput[StructuralDiagnosis]:
        features: list[StructuralFeature] = []
        score = 0.0
        state = StructuralState.UNKNOWN
        secondary: StructuralState | None = None
        notes: list[str] = []

        if payload.bars_seen < 2:
            diag = StructuralDiagnosis(state=state, features=features, score=0.0, notes=["insufficient_data"])
            return self.wrap(payload=diag, ctx=ctx, confidence=0.05, visibility="degraded")

        if payload.range_pct >= self.EXPANSION_RANGE_PCT:
            state = StructuralState.EXPANSION
            score += 0.4
            features.append(StructuralFeature(name="range_pct", value=payload.range_pct))
        elif payload.range_pct <= self.COMPRESSION_RANGE_PCT:
            state = StructuralState.COMPRESSION
            score += 0.3
            features.append(StructuralFeature(name="range_pct", value=payload.range_pct))

        if payload.body_ratio >= self.DISPLACEMENT_BODY_RATIO and abs(payload.return_pct) > 0:
            secondary = state if state != StructuralState.UNKNOWN else None
            state = StructuralState.DISPLACEMENT
            score += 0.25
            features.append(StructuralFeature(name="body_ratio", value=payload.body_ratio))

        if max(payload.upper_wick_ratio, payload.lower_wick_ratio) >= self.EXHAUSTION_WICK_RATIO:
            if state == StructuralState.UNKNOWN:
                state = StructuralState.EXHAUSTION
            else:
                secondary = StructuralState.EXHAUSTION
            score += 0.2
            features.append(
                StructuralFeature(
                    name="wick_max",
                    value=max(payload.upper_wick_ratio, payload.lower_wick_ratio),
                )
            )

        if payload.volume_z >= self.ABSORPTION_VOL_Z and payload.body_ratio < 0.4:
            if state == StructuralState.UNKNOWN:
                state = StructuralState.ABSORPTION
            else:
                secondary = StructuralState.ABSORPTION
            score += 0.2
            features.append(StructuralFeature(name="volume_z", value=payload.volume_z))

        if state == StructuralState.UNKNOWN:
            if abs(payload.return_pct) < 0.002:
                state = StructuralState.RANGE
            elif payload.return_pct > 0:
                state = StructuralState.TREND_UP
            else:
                state = StructuralState.TREND_DOWN
            score = 0.1

        diag = StructuralDiagnosis(
            state=state,
            secondary_state=secondary,
            features=features,
            score=safe_prob(score),
            notes=notes,
        )
        confidence = min(1.0, score)
        return self.wrap(payload=diag, ctx=ctx, confidence=confidence, visibility="full")
