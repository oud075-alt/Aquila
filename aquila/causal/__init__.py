"""Causal inference graph subsystem.

Distinguishes:
- correlation
- structural dependency
- causal escalation
- temporal causality

Bounded scope: in-process DAG over LayerOutput event_ids. Not statistical
causal inference (no do-calculus, no learned graphs); a typed, transparent
edge ledger that records: which upstream output caused which downstream.
"""

from aquila.causal.engine import CausalGraphEngine
from aquila.causal.schemas import CausalEdge, CausalEdgeKind, CausalGraph

__all__ = ["CausalGraphEngine", "CausalEdge", "CausalEdgeKind", "CausalGraph"]
