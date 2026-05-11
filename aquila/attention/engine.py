from __future__ import annotations

from aquila.attention.schemas import AttentionReport, SalienceScore
from aquila.core.base import LayerOutput
from aquila.core.numeric import safe_prob
from aquila.core.types import LayerName


class AttentionAllocator:
    def allocate(self, outputs: dict[LayerName, LayerOutput], top_k: int = 5) -> AttentionReport:
        scores: list[SalienceScore] = []
        weights = {
            LayerName.DECEPTION: 1.0,
            LayerName.PATHOLOGY: 0.9,
            LayerName.REGIME: 0.8,
            LayerName.META: 0.7,
            LayerName.TEMPORAL: 0.6,
            LayerName.MEMORY: 0.5,
            LayerName.STRUCTURAL: 0.4,
            LayerName.PRIMITIVES: 0.1,
        }
        for ln, o in outputs.items():
            base = o.confidence * weights.get(ln, 0.3)
            penalty = 0.2 if o.visibility in ("degraded", "blind") else 0.0
            salience = safe_prob(base - penalty)
            scores.append(SalienceScore(
                layer=ln, event_id=o.event_id, salience=salience,
                reason=f"conf={o.confidence:.2f} weight={weights.get(ln, 0.3):.2f}",
            ))
        scores.sort(key=lambda s: s.salience, reverse=True)
        return AttentionReport(top=scores[:top_k])
