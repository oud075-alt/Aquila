"""Layer 8 engine — Meta-Cognition."""

from __future__ import annotations

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.numeric import safe_prob
from aquila.core.types import LayerName
from aquila.meta.confidence_graph import build_confidence_graph
from aquila.meta.interfaces import MetaCognitionService
from aquila.meta.reflexivity import assert_within_bound
from aquila.meta.schemas import MetaCognitiveReport, MetaSignal
from aquila.meta.self_consistency import check_self_consistency
from aquila.meta.uncertainty import compute_uncertainty
from aquila.meta.visibility import low_visibility_layers


class MetaCognitionLayer(MetaCognitionService):
    layer_name = LayerName.META

    def __init__(self, reflexive_depth: int = 0) -> None:
        super().__init__()
        assert_within_bound(reflexive_depth)
        self._depth = reflexive_depth

    def process(self, payload: dict, ctx: LayerContext) -> LayerOutput[MetaCognitiveReport]:
        outputs = {ln: o for ln, o in ctx.upstream_outputs.items() if ln != LayerName.META}

        u = compute_uncertainty(outputs)
        g = build_confidence_graph(outputs)
        sc = check_self_consistency(outputs)
        lv = low_visibility_layers(outputs)

        cognitive_health = safe_prob(1.0 - u.total)
        elevated = u.total > 0.6 or not sc.consistent or len(lv) >= 2
        cap = 0.4 if elevated else None
        notes: list[str] = list(sc.conflicts)
        if lv:
            notes.append("low_visibility:" + ",".join(l.value for l in lv))

        report = MetaCognitiveReport(
            uncertainty=u,
            confidence_graph=g,
            self_consistency=sc,
            low_visibility_layers=lv,
            cognitive_health=cognitive_health,
            meta_signal=MetaSignal(
                elevated_uncertainty=elevated,
                cap_downstream_confidence=cap,
                notes=notes,
            ),
        )
        return self.wrap(payload=report, ctx=ctx, confidence=cognitive_health, visibility="full")
