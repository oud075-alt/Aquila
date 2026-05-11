from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.numeric import safe_prob
from aquila.core.types import LayerName
from aquila.meta.schemas import UncertaintyModel


def compute_uncertainty(outputs: dict[LayerName, LayerOutput]) -> UncertaintyModel:
    if not outputs:
        return UncertaintyModel(epistemic=1.0, aleatoric=0.5, visibility_penalty=1.0)
    confs = [o.confidence for o in outputs.values()]
    avg_conf = sum(confs) / len(confs)
    epistemic = safe_prob(1.0 - avg_conf)

    vis_penalty = 0.0
    for o in outputs.values():
        if o.visibility == "degraded":
            vis_penalty += 0.1
        elif o.visibility == "blind":
            vis_penalty += 0.2
        elif o.visibility == "partial":
            vis_penalty += 0.05

    contra = 0.0
    pat = outputs.get(LayerName.PATHOLOGY)
    if pat is not None:
        contra = safe_prob(getattr(pat.payload, "aggregate_contradiction_score", 0.0))

    return UncertaintyModel(
        epistemic=epistemic,
        aleatoric=safe_prob(1.0 - max(confs) if confs else 0.5),
        visibility_penalty=safe_prob(vis_penalty),
        contradiction_penalty=contra,
    )
