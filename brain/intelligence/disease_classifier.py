"""Disease classifier.

Maps the standardized pathology scores + regime + contradiction signals
to a :class:`DiagnosisLabel` and pathology :class:`SeverityLevel`.

Decision logic is explicit and ranked: higher-priority pathologies
override lower-priority observations (per DIAGNOSTIC PRIORITY HIERARCHY).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from brain.math_core import clamp
from brain.schemas import (
    ContradictionScores,
    DiagnosisLabel,
    PathologyScores,
    RegimeLabel,
    SeverityLevel,
)
from config import get_market_config


@dataclass
class Classification:
    label: DiagnosisLabel
    severity: SeverityLevel
    reasoning: List[str]
    score: float


class DiseaseClassifier:
    def __init__(self):
        self.thresholds = get_market_config().thresholds

    def classify(
        self,
        pathology: PathologyScores,
        contradiction: ContradictionScores,
        regime: RegimeLabel,
        compression_release_prob: float,
    ) -> Classification:
        aggregate = pathology.aggregate()
        reasoning: List[str] = []

        # --- Disease label (priority ordered) -----------------------------
        if pathology.pre_collapse >= 0.65 and pathology.structural_instability >= 0.50:
            label = DiagnosisLabel.PRE_COLLAPSE
            reasoning.append("Pre-collapse fusion ≥0.65 with structural instability ≥0.50.")
        elif pathology.structural_instability >= 0.65 and pathology.entropy_disorder >= 0.50:
            label = DiagnosisLabel.CHAOTIC_TRANSITION
            reasoning.append("Structural instability and entropy disorder both elevated.")
        elif pathology.hidden_exhaustion >= 0.55 and pathology.behavioral_divergence >= 0.50:
            label = DiagnosisLabel.STRUCTURAL_EXHAUSTION
            reasoning.append("Hidden exhaustion + divergence confirmed.")
        elif pathology.manipulation_footprint >= 0.55 and pathology.liquidity_fragility >= 0.50:
            label = DiagnosisLabel.MANIPULATIVE_ENVIRONMENT
            reasoning.append("Manipulation footprint + liquidity fragility above thresholds.")
        elif pathology.liquidity_fragility >= 0.60 and pathology.stress_escalation >= 0.45:
            label = DiagnosisLabel.LIQUIDITY_STRESS_BUILDUP
            reasoning.append("Liquidity fragility with rising stress signature.")
        elif pathology.acceptance_failure >= 0.55 and pathology.continuation_failure >= 0.45:
            label = DiagnosisLabel.FRAGILE_BREAKOUT
            reasoning.append("Acceptance failure with continuation failure — fragile breakout.")
        elif pathology.hidden_exhaustion >= 0.45 and contradiction.volume_vs_price >= 0.40:
            label = DiagnosisLabel.HIDDEN_DISTRIBUTION
            reasoning.append("Hidden exhaustion alongside volume contradiction.")
        elif pathology.compression_pressure >= 0.55 and compression_release_prob >= 0.50:
            label = DiagnosisLabel.PRE_EXPANSION_COMPRESSION
            reasoning.append("Compression pressure with elevated release probability.")
        elif regime in (RegimeLabel.EXPANSION,) and pathology.structural_instability >= 0.45:
            label = DiagnosisLabel.UNSTABLE_EXPANSION
            reasoning.append("Expansion regime with elevated instability.")
        elif regime in (RegimeLabel.TREND_UP, RegimeLabel.TREND_DOWN) and aggregate < 0.30:
            label = DiagnosisLabel.HEALTHY_TREND
            reasoning.append("Trending regime with low aggregated pathology — healthy trend.")
        elif regime == RegimeLabel.EXPANSION and aggregate < 0.30:
            label = DiagnosisLabel.HEALTHY_EXPANSION
            reasoning.append("Expansion regime with minimal pathology — healthy expansion.")
        elif regime == RegimeLabel.COMPRESSION and aggregate < 0.30:
            label = DiagnosisLabel.HEALTHY_COMPRESSION
            reasoning.append("Compression regime with stable internal structure — healthy compression.")
        elif regime == RegimeLabel.CHAOTIC:
            label = DiagnosisLabel.CHAOTIC_TRANSITION
            reasoning.append("Chaotic regime without a single dominant pathology cluster.")
        elif aggregate >= 0.45:
            # Aggregate pathology is elevated but no single cluster passes the
            # specific threshold — surface this as fragile structure rather
            # than UNDETERMINED so severity and label remain consistent.
            label = DiagnosisLabel.FRAGILE_BREAKOUT
            reasoning.append("Elevated aggregate pathology without a dominant cluster — fragile structure.")
        else:
            label = DiagnosisLabel.UNDETERMINED
            reasoning.append("No dominant pathology cluster — diagnosis undetermined.")

        # --- Severity hierarchy ------------------------------------------
        severity = self._severity_from_score(aggregate, pathology)
        return Classification(label=label, severity=severity, reasoning=reasoning, score=aggregate)

    def _severity_from_score(self, aggregate: float, pathology: PathologyScores) -> SeverityLevel:
        # Structural failure: extreme pre-collapse + instability + stress.
        if (
            pathology.pre_collapse >= 0.85
            and pathology.structural_instability >= 0.75
            and pathology.stress_escalation >= 0.65
        ):
            return SeverityLevel.STRUCTURAL_FAILURE
        t = self.thresholds
        if aggregate >= t.pre_collapse:
            return SeverityLevel.PRE_COLLAPSE
        if aggregate >= t.high_risk:
            return SeverityLevel.HIGH_RISK_TRANSITION
        if aggregate >= t.fragile:
            return SeverityLevel.FRAGILE_STRUCTURE
        if aggregate >= t.minor:
            return SeverityLevel.MINOR_INSTABILITY
        return SeverityLevel.HEALTHY_STRUCTURE
