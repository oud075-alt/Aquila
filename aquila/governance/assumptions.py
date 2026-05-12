"""Assumption registry. Closes audit gap #53.

Each assumption MUST point at a real pytest node id via ``falsifiable_by``.
An empty ``falsifiable_by`` means the claim is *not yet* falsifiable in
the codebase and therefore must be treated as unproven by the validation
suite.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Assumption(BaseModel):
    model_config = ConfigDict(frozen=True)
    namespace: str
    name: str
    statement: str
    # pytest node id (e.g. "tests/falsification/test_xx.py::test_yy").
    # Empty string means "no test exists yet" → counted as unproven.
    falsifiable_by: str = ""
    risk_if_violated: str = ""


class AssumptionRegistry:
    def __init__(self) -> None:
        self._a: list[Assumption] = []
        self._seed()

    def _seed(self) -> None:
        self._a.extend([
            Assumption(
                namespace="structural",
                name="bar_closed_data",
                statement="L1/L2 operate on bar-closed OHLCV, not intra-bar",
                falsifiable_by=(
                    "tests/falsification/test_bar_closed_data.py"
                    "::test_intra_bar_does_not_change_diagnosis"
                ),
                risk_if_violated="non-deterministic structural diagnosis",
            ),
            Assumption(
                namespace="deception",
                name="no_signal_emission",
                statement="L6 emits no fields resembling trade signals",
                falsifiable_by=(
                    "tests/falsification/test_no_signal_emission.py"
                    "::test_safety_kernel_rejects_signal_field"
                ),
                risk_if_violated="violates non-trading mandate",
            ),
            Assumption(
                namespace="memory",
                name="origin_isolation",
                statement="synthetic/replay events do not write to real memory archive",
                falsifiable_by=(
                    "tests/falsification/test_origin_isolation.py"
                    "::test_synthetic_never_writes_real_archive"
                ),
                risk_if_violated="contaminated analogs",
            ),
            Assumption(
                namespace="meta",
                name="bounded_reflexivity",
                statement="Meta recursion depth <= 1",
                falsifiable_by=(
                    "tests/falsification/test_bounded_reflexivity.py"
                    "::test_meta_depth_above_one_raises"
                ),
                risk_if_violated="infinite meta loops",
            ),
        ])

    def register(self, a: Assumption) -> None:
        self._a.append(a)

    def all(self) -> list[Assumption]:
        return list(self._a)
