"""Formal structural ontology system.

Canonical taxonomies + versioned registry:
- structural states (mirrors L2)
- pathologies (mirrors L3)
- regimes (mirrors L7)
- deception kinds (mirrors L6)
- liquidity classes

The registry enables ontology evolution while preserving replay
compatibility (every record carries a `schema_version`).
"""

from aquila.ontology.liquidity import LiquidityClass, LIQUIDITY_ONTOLOGY
from aquila.ontology.registry import OntologyRegistry
from aquila.ontology.schemas import OntologyEntry, OntologySnapshot

__all__ = [
    "LiquidityClass",
    "LIQUIDITY_ONTOLOGY",
    "OntologyRegistry",
    "OntologyEntry",
    "OntologySnapshot",
]
