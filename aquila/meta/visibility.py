from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName


def low_visibility_layers(outputs: dict[LayerName, LayerOutput]) -> list[LayerName]:
    bad = {"degraded", "blind"}
    return [ln for ln, o in outputs.items() if o.visibility in bad]
