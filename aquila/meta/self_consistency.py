from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName
from aquila.meta.schemas import SelfConsistencyResult


def check_self_consistency(outputs: dict[LayerName, LayerOutput]) -> SelfConsistencyResult:
    conflicts: list[str] = []

    structural = outputs.get(LayerName.STRUCTURAL)
    pathology = outputs.get(LayerName.PATHOLOGY)
    deception = outputs.get(LayerName.DECEPTION)
    temporal = outputs.get(LayerName.TEMPORAL)

    if pathology is not None and structural is not None:
        if getattr(pathology.payload, "aggregate_pathology_score", 0.0) > 0.6 and structural.confidence > 0.8:
            conflicts.append("high_pathology_with_high_structural_confidence")

    if deception is not None and structural is not None:
        if getattr(deception.payload, "deception_probability", 0.0) > 0.6 and structural.confidence > 0.7:
            conflicts.append("high_deception_with_high_structural_confidence")

    if temporal is not None and structural is not None:
        cg = getattr(temporal.payload, "conflict_graph", None)
        if cg is not None and getattr(cg, "aggregate_conflict", 0.0) > 0.5 and structural.confidence > 0.7:
            conflicts.append("temporal_conflict_with_high_structural_confidence")

    return SelfConsistencyResult(consistent=not conflicts, conflicts=conflicts)
