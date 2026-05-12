"""Per-cycle event lineage graph (module path retained for compatibility).

Bounded scope: in-process DAG over ``LayerOutput.event_id`` values. Not
statistical causal inference (no do-calculus, no learned graphs); a
typed, transparent edge ledger that records which upstream output was
cited by which downstream output.

Public surface:

- :class:`LineageGraph`   — the honest name.
- :class:`CausalGraphEngine` — deprecation alias (see ADR-0009).
- :class:`CausalEdge` / :class:`CausalEdgeKind` / :class:`CausalGraph`
  schemas retained unchanged in this PR; their rename is intentionally
  deferred because they cross the wire (FastAPI, JSON-LD export) and
  renaming them now would require a schema bump that this single rename
  PR is not the right place for.
"""

from aquila.causal.engine import CausalGraphEngine, LineageGraph
from aquila.causal.schemas import CausalEdge, CausalEdgeKind, CausalGraph

__all__ = [
    "LineageGraph",
    "CausalGraphEngine",
    "CausalEdge",
    "CausalEdgeKind",
    "CausalGraph",
]
