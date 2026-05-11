"""Layer 6 engine — Deception Intelligence."""

from __future__ import annotations

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.confidence import ConfidenceCalculus
from aquila.core.types import LayerName
from aquila.deception.interfaces import DeceptionService
from aquila.deception.lure import HeuristicLureClassifier
from aquila.deception.narrative import narrative_divergence
from aquila.deception.safety import assert_no_signal
from aquila.deception.schemas import DeceptionReport
from aquila.deception.traps import StructuralTrapDetector
from aquila.pathology.schemas import PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis


class DeceptionIntelligenceLayer(DeceptionService):
    layer_name = LayerName.DECEPTION

    def __init__(
        self,
        trap_detector=None,
        lure_classifier=None,
    ) -> None:
        super().__init__()
        self._traps = trap_detector or StructuralTrapDetector()
        self._lures = lure_classifier or HeuristicLureClassifier()

    def process(
        self, payload: PathologyReport, ctx: LayerContext
    ) -> LayerOutput[DeceptionReport]:
        struct_out = ctx.upstream_outputs.get(LayerName.STRUCTURAL)
        prim_out = ctx.upstream_outputs.get(LayerName.PRIMITIVES)
        if struct_out is None:
            rep = DeceptionReport()
            assert_no_signal(rep)
            return self.wrap(payload=rep, ctx=ctx, confidence=0.0, visibility="blind")

        diag: StructuralDiagnosis = struct_out.payload  # type: ignore[assignment]
        snap: PrimitiveSnapshot | None = prim_out.payload if prim_out else None  # type: ignore[assignment]

        sigs = self._traps.detect(structural=diag, pathology=payload, primitives=snap)
        lures = self._lures.classify(structural=diag, pathology=payload, primitives=snap)
        narr = narrative_divergence(diag, payload, snap)

        agg = ConfidenceCalculus.combine_independent(
            [s.probability for s in sigs]
            + [lu.probability for lu in lures]
            + [narr.score]
        )

        rep = DeceptionReport(
            deception_probability=agg,
            signatures=sigs,
            lures=lures,
            narrative=narr,
        )
        assert_no_signal(rep)

        return self.wrap(
            payload=rep, ctx=ctx, confidence=agg, visibility="full",
            evidence=[struct_out.as_ref()],
        )
