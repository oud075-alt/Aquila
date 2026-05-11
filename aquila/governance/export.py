"""Cognition export — JSON-LD-flavored payload for external review.

Closes audit gap #66.
"""

from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName


class CognitionExporter:
    CONTEXT = {
        "@vocab": "https://aquila.local/ontology#",
        "Layer": "Layer",
        "Output": "Output",
    }

    def export(self, outputs: dict[LayerName, LayerOutput]) -> dict:
        items = []
        for ln, o in outputs.items():
            items.append({
                "@type": "Output",
                "layer": ln.value,
                "event_id": o.event_id,
                "correlation_id": o.correlation_id,
                "timestamp": o.timestamp.isoformat(),
                "confidence": o.confidence,
                "visibility": o.visibility,
                "schema_version": o.schema_version,
                "evidence": [ref.event_id for ref in o.evidence],
                "payload": o.payload.model_dump() if hasattr(o.payload, "model_dump") else {},
            })
        return {"@context": self.CONTEXT, "outputs": items}
