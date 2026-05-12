"""Heuristic confidence-score fusion (module name retained for import path).

The module historically advertised "Bayesian-flavored confidence
propagation". The implementation is a weighted-mean fuser, not a
Bayesian posterior calculator. ADR-0006 documents the rename to
``HeuristicScoreFuser``; ``BayesianReasoner`` is kept as a deprecation
alias.
"""

from aquila.probabilistic.bayes import BayesianReasoner, HeuristicScoreFuser
from aquila.probabilistic.schemas import Evidence, PosteriorBelief

__all__ = [
    "HeuristicScoreFuser",
    "BayesianReasoner",
    "Evidence",
    "PosteriorBelief",
]
