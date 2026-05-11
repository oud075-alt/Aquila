"""Shadow execution — run an alternate orchestrator config alongside the
real one and compare outputs without mutating real cognition state.

Closes audit gap #64.
"""

from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName, Symbol
from aquila.pipeline import CognitiveOrchestrator
from aquila.primitives import PrimitiveBar


class ShadowExecutor:
    def __init__(self, control: CognitiveOrchestrator, shadow: CognitiveOrchestrator) -> None:
        self._control = control
        self._shadow = shadow

    def run_tick(
        self, symbol: Symbol, bar: PrimitiveBar
    ) -> tuple[dict[LayerName, LayerOutput], dict[LayerName, LayerOutput], dict]:
        c = self._control.run_tick(symbol, bar)
        s = self._shadow.run_tick(symbol, bar)
        diff = {
            ln.value: {"control": c[ln].confidence, "shadow": s[ln].confidence}
            for ln in c if ln in s
        }
        return c, s, diff
