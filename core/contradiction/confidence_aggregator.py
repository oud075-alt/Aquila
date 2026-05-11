"""Confidence aggregator (Appendix F + O).

Weighted geometric mean of per-module confidences, multiplied by an
exponential penalty for instability, contradiction, and entropy.

This module produces the SOLE `ConfidenceState`; the orchestrator is the
only place permitted to invoke it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from core.pathology.metrics import EPS, clip01
from core.schemas.confidence_state import ConfidenceState
from core.schemas.enums import SourceMode, Timeframe

LAMBDA_INSTABILITY: float = 1.25
LAMBDA_CONTRADICTION: float = 1.00
LAMBDA_ENTROPY: float = 0.75


@dataclass(frozen=True, slots=True)
class PerModuleConfidence:
    name: str
    value: float
    weight: float = 1.0


class ConfidenceAggregator:
    """Compute global confidence per Appendix O."""

    def __init__(
        self,
        lambda_instability: float = LAMBDA_INSTABILITY,
        lambda_contradiction: float = LAMBDA_CONTRADICTION,
        lambda_entropy: float = LAMBDA_ENTROPY,
    ) -> None:
        if lambda_instability < 0 or lambda_contradiction < 0 or lambda_entropy < 0:
            raise ValueError("lambda penalties must be non-negative")
        self.lambda_instability = lambda_instability
        self.lambda_contradiction = lambda_contradiction
        self.lambda_entropy = lambda_entropy

    def aggregate(
        self,
        contributors: list[PerModuleConfidence],
        *,
        instability_score: float,
        contradiction_score: float,
        entropy_score: float,
        timestamp: datetime,
        timeframe: Timeframe,
        source: SourceMode,
    ) -> ConfidenceState:
        if not contributors:
            raise ValueError("at least one contributor is required")
        total_weight = sum(max(c.weight, 0.0) for c in contributors)
        if total_weight <= 0:
            raise ValueError("contributor weights must sum to a positive value")

        log_sum = 0.0
        for c in contributors:
            v = clip01(c.value)
            log_sum += (c.weight / total_weight) * math.log(v + EPS)
        gm = math.exp(log_sum)

        ip = math.exp(-self.lambda_instability * clip01(instability_score))
        cp = math.exp(-self.lambda_contradiction * clip01(contradiction_score))
        ep = math.exp(-self.lambda_entropy * clip01(entropy_score))

        global_conf = clip01(gm * ip * cp * ep)

        return ConfidenceState(
            timestamp=timestamp,
            timeframe=timeframe,
            source=source,
            confidence=global_conf,
            raw_geometric_mean=clip01(gm),
            instability_penalty=clip01(ip),
            contradiction_penalty=clip01(cp),
            entropy_penalty=clip01(ep),
            global_confidence=global_conf,
            contributors=tuple(c.name for c in contributors),
            lambda1=self.lambda_instability,
            lambda2=self.lambda_contradiction,
            lambda3=self.lambda_entropy,
        )
