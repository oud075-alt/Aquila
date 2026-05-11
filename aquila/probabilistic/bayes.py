from __future__ import annotations

from aquila.core.confidence import ConfidenceCalculus
from aquila.core.numeric import safe_prob
from aquila.probabilistic.schemas import Evidence, PosteriorBelief


class BayesianReasoner:
    @staticmethod
    def update(hypothesis: str, prior: float, evidence: list[Evidence]) -> PosteriorBelief:
        if not evidence:
            return PosteriorBelief(hypothesis=hypothesis, prior=prior, posterior=safe_prob(prior))
        agg = ConfidenceCalculus.weighted_mean([(e.weight, e.likelihood) for e in evidence])
        posterior = ConfidenceCalculus.weighted_mean([(1.0, prior), (sum(e.weight for e in evidence), agg)])
        return PosteriorBelief(
            hypothesis=hypothesis, prior=safe_prob(prior),
            posterior=safe_prob(posterior), evidence=evidence,
        )
