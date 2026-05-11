from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import LayerName


class LayerSLA(BaseModel):
    model_config = ConfigDict(frozen=True)
    layer: LayerName
    p50_latency_ms: float = 50.0
    p99_latency_ms: float = 250.0


class SLARegistry(BaseModel):
    model_config = ConfigDict(frozen=True)
    slas: dict[LayerName, LayerSLA] = Field(default_factory=lambda: {
        ln: LayerSLA(layer=ln) for ln in LayerName
    })
