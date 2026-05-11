"""Probabilistic reasoning framework.

Bayesian-flavored confidence propagation + evidence weighting + decay.
Wraps `ConfidenceCalculus` for higher-level use by L8 and the attention
allocator.
"""

from aquila.probabilistic.bayes import BayesianReasoner
from aquila.probabilistic.schemas import Evidence, PosteriorBelief

__all__ = ["BayesianReasoner", "Evidence", "PosteriorBelief"]
