"""Liquidity ontology — classification taxonomy."""

from __future__ import annotations

from enum import Enum

from aquila.ontology.schemas import OntologyEntry


class LiquidityClass(str, Enum):
    PASSIVE = "passive_liquidity"
    AGGRESSIVE = "aggressive_liquidity"
    TRAPPED = "trapped_liquidity"
    SYNTHETIC = "synthetic_liquidity"
    VOID = "liquidity_void"
    ABSORPTION = "absorption_zone"


LIQUIDITY_ONTOLOGY: tuple[OntologyEntry, ...] = tuple(
    OntologyEntry(namespace="liquidity", name=lc.value, description=f"Liquidity class: {lc.value}")
    for lc in LiquidityClass
)
