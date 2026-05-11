"""Liquidity-lure classifier."""

from __future__ import annotations

from aquila.core.numeric import safe_prob
from aquila.deception.interfaces import LureClassifier
from aquila.deception.schemas import LureClassification
from aquila.pathology.schemas import PathologyReport
from aquila.primitives.schemas import PrimitiveSnapshot
from aquila.structural.schemas import StructuralDiagnosis, StructuralState


class HeuristicLureClassifier(LureClassifier):
    """Heuristic lure detection. NOT a signal generator — outputs only
    structural lure probability and an abstract zone hint, never a price/
    direction/action.
    """

    def classify(
        self,
        *,
        structural: StructuralDiagnosis,
        pathology: PathologyReport,
        primitives: PrimitiveSnapshot | None,
    ) -> list[LureClassification]:
        out: list[LureClassification] = []
        if primitives is None:
            return out

        if structural.state == StructuralState.EXPANSION and primitives.volume_z < -0.2:
            out.append(LureClassification(
                lure_type="expansion_lure",
                probability=safe_prob(0.5),
                target_zone_hint="prior_swing_band",
            ))
        if structural.state == StructuralState.COMPRESSION and pathology.aggregate_contradiction_score > 0.4:
            out.append(LureClassification(
                lure_type="compression_lure",
                probability=safe_prob(0.6),
                target_zone_hint="liquidity_pocket_outside_range",
            ))
        if primitives.upper_wick_ratio > 0.6 or primitives.lower_wick_ratio > 0.6:
            out.append(LureClassification(
                lure_type="wick_lure",
                probability=safe_prob(0.45),
                target_zone_hint="post_wick_zone",
            ))
        return out
