from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Symbol


class LayerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    primitives_window: int = 50
    memory_top_k: int = 5
    memory_sequence_n: int = 3
    vol_low: float = 0.005
    vol_high: float = 0.02


class AquilaSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    default: LayerSettings = LayerSettings()
    overrides: dict[Symbol, LayerSettings] = Field(default_factory=dict)

    def for_symbol(self, symbol: Symbol) -> LayerSettings:
        return self.overrides.get(symbol, self.default)
