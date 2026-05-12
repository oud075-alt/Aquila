"""Heuristic score fusion (legacy module name retained for import path).

The actual algorithm here is NOT a Bayesian posterior update. It is a
weighted-mean fusion of evidence likelihoods with a prior, using the
``ConfidenceCalculus.weighted_mean`` helper. See
``docs/adr/ADR-0006-rename-bayesian-reasoner.md`` for the full
discussion.

Public surface:

- ``HeuristicScoreFuser`` — the honest name.
- ``BayesianReasoner``    — deprecation alias. Emits
   ``DeprecationWarning`` on construction or class access. Will be
   removed two PRs after the rename per HARD RULE #8.
"""

from __future__ import annotations

import warnings

from aquila.core.confidence import ConfidenceCalculus
from aquila.core.numeric import safe_prob
from aquila.probabilistic.schemas import Evidence, PosteriorBelief


class HeuristicScoreFuser:
    """Fuse evidence likelihoods with a prior using weighted means.

    The method intentionally does NOT compute a posterior in the
    Bayesian sense (no likelihood ratios, no normalisation over
    competing hypotheses, no use of ``P(E|H)`` and ``P(E|¬H)``). It
    produces a single fused confidence score that is bounded to
    ``[0, 1]`` by ``safe_prob``.
    """

    @staticmethod
    def fuse(hypothesis: str, prior: float, evidence: list[Evidence]) -> PosteriorBelief:
        if not evidence:
            return PosteriorBelief(
                hypothesis=hypothesis,
                prior=safe_prob(prior),
                posterior=safe_prob(prior),
            )
        agg = ConfidenceCalculus.weighted_mean(
            [(e.weight, e.likelihood) for e in evidence]
        )
        fused = ConfidenceCalculus.weighted_mean(
            [(1.0, prior), (sum(e.weight for e in evidence), agg)]
        )
        return PosteriorBelief(
            hypothesis=hypothesis,
            prior=safe_prob(prior),
            posterior=safe_prob(fused),
            evidence=evidence,
        )

    # Backwards-compatible signature ``update`` — kept so existing call
    # sites (tests, external consumers) don't break in this PR. ``fuse``
    # is the canonical name. ``update`` will be removed in the same PR
    # cycle that deletes the ``BayesianReasoner`` alias.
    @staticmethod
    def update(hypothesis: str, prior: float, evidence: list[Evidence]) -> PosteriorBelief:
        return HeuristicScoreFuser.fuse(hypothesis, prior, evidence)


class _DeprecatedBayesianReasonerMeta(type):
    """Emit ``DeprecationWarning`` on every access of the legacy class."""

    def __getattribute__(cls, item):
        if item not in {"__class__", "__name__", "__qualname__", "__mro__"}:
            warnings.warn(
                "BayesianReasoner is deprecated; use HeuristicScoreFuser. "
                "The legacy name will be removed two PRs after the rename "
                "(see ADR-0006).",
                DeprecationWarning,
                stacklevel=2,
            )
        return super().__getattribute__(item)


class BayesianReasoner(HeuristicScoreFuser, metaclass=_DeprecatedBayesianReasonerMeta):
    """Deprecated alias for :class:`HeuristicScoreFuser`.

    Kept per HARD RULE #8. Do not extend or add behaviour here.
    """

    pass
