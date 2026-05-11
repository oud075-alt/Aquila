"""Engineered-manipulation signature library.

The library is data-driven so it can evolve via the protocol-versioned
ontology without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aquila.deception.schemas import DeceptionKind


@dataclass(frozen=True)
class ManipulationPattern:
    name: str
    deception_kind: DeceptionKind
    required_pathologies: tuple[str, ...] = field(default_factory=tuple)
    required_states: tuple[str, ...] = field(default_factory=tuple)
    minimum_wick_ratio: float = 0.0
    minimum_volume_z: float = 0.0


SIGNATURE_LIBRARY: tuple[ManipulationPattern, ...] = (
    ManipulationPattern(
        name="bull_trap_classic",
        deception_kind=DeceptionKind.BULL_TRAP,
        required_states=("displacement", "trend_up"),
        minimum_wick_ratio=0.55,
        minimum_volume_z=1.0,
    ),
    ManipulationPattern(
        name="bear_trap_classic",
        deception_kind=DeceptionKind.BEAR_TRAP,
        required_states=("displacement", "trend_down"),
        minimum_wick_ratio=0.55,
        minimum_volume_z=1.0,
    ),
    ManipulationPattern(
        name="absorption_deception",
        deception_kind=DeceptionKind.ABSORPTION_DECEPTION,
        required_pathologies=("absorption_on_displacement",),
    ),
)
