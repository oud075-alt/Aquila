"""Assumption registry. Closes audit gap #53."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Assumption(BaseModel):
    model_config = ConfigDict(frozen=True)
    namespace: str
    name: str
    statement: str
    falsifiable_by: str = ""
    risk_if_violated: str = ""


class AssumptionRegistry:
    def __init__(self) -> None:
        self._a: list[Assumption] = []
        self._seed()

    def _seed(self) -> None:
        self._a.extend([
            Assumption(namespace="structural", name="bar_closed_data",
                       statement="L1/L2 operate on bar-closed OHLCV, not intra-bar",
                       falsifiable_by="intra-bar replay producing different results",
                       risk_if_violated="non-deterministic structural diagnosis"),
            Assumption(namespace="deception", name="no_signal_emission",
                       statement="L6 emits no fields resembling trade signals",
                       falsifiable_by="Safety Kernel scan",
                       risk_if_violated="violates non-trading mandate"),
            Assumption(namespace="memory", name="origin_isolation",
                       statement="synthetic/replay events do not write to real memory archive",
                       falsifiable_by="audit of MemoryStore writes by origin",
                       risk_if_violated="contaminated analogs"),
            Assumption(namespace="meta", name="bounded_reflexivity",
                       statement="Meta recursion depth <= 1",
                       falsifiable_by="reflexivity.assert_within_bound",
                       risk_if_violated="infinite meta loops"),
        ])

    def register(self, a: Assumption) -> None:
        self._a.append(a)

    def all(self) -> list[Assumption]:
        return list(self._a)
