from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName
from aquila.meta.schemas import CognitiveConfidenceEdge, CognitiveConfidenceGraph


def build_confidence_graph(outputs: dict[LayerName, LayerOutput]) -> CognitiveConfidenceGraph:
    edges = [
        CognitiveConfidenceEdge(layer=ln, confidence=o.confidence, visibility=o.visibility)
        for ln, o in outputs.items()
    ]
    return CognitiveConfidenceGraph(edges=edges)
