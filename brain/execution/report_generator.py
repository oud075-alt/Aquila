"""Report generator — assemble human-readable diagnostic reports."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from brain.schemas import StandardizedDiagnosis


class ReportGenerator:
    """Produces markdown / plain-text reports from a diagnosis."""

    def build_markdown(self, diag: StandardizedDiagnosis) -> str:
        ps = diag.pathology_scores.as_dict()
        cs = diag.contradiction_scores.as_dict()
        ranked = sorted(ps.items(), key=lambda kv: kv[1], reverse=True)
        c_ranked = sorted(cs.items(), key=lambda kv: kv[1], reverse=True)

        ts = diag.timestamp.isoformat() if isinstance(diag.timestamp, datetime) else str(diag.timestamp)

        lines = [
            f"# MSPIS Structural Diagnosis — {diag.symbol} {diag.timeframe}",
            "",
            f"- Timestamp: `{ts}`",
            f"- Exchange: `{diag.exchange}`",
            f"- Market State: **{diag.market_state.value}**",
            f"- Severity: **{diag.severity.value}**",
            f"- Regime: `{diag.regime.value}`",
            f"- Overall Pathology: `{diag.overall_pathology():.3f}`",
            f"- Confidence: `{diag.confidence_scores.overall_confidence:.3f}`",
            f"- Structural Health: `{diag.structural_health.score:.3f}` ({diag.structural_health.summary})",
            "",
            "## Pathology Scores",
        ]
        for name, value in ranked:
            lines.append(f"- {name}: `{value:.3f}`")
        lines += ["", "## Contradiction Scores"]
        for name, value in c_ranked:
            lines.append(f"- {name}: `{value:.3f}`")

        lines += [
            "",
            "## Volatility State",
            f"- Realized vol: `{diag.volatility_state.realized_vol:.5f}` (expected `{diag.volatility_state.expected_vol:.5f}`)",
            f"- Vol-of-vol: `{diag.volatility_state.vol_of_vol:.5f}`",
            f"- Compression / Expansion: `{diag.volatility_state.compression_ratio:.2f}` / `{diag.volatility_state.expansion_ratio:.2f}` ({diag.volatility_state.label})",
            "",
            "## Liquidity State",
            f"- Participation: `{diag.liquidity_state.participation:.3f}` (expected `{diag.liquidity_state.expected_participation:.3f}`)",
            f"- Imbalance: `{diag.liquidity_state.imbalance:.3f}`",
            f"- Sweep frequency: `{diag.liquidity_state.sweep_frequency:.3f}`",
            f"- Fragility score: `{diag.liquidity_state.fragility_score:.3f}` ({diag.liquidity_state.label})",
            "",
            "## Continuation State",
            f"- Persistence: `{diag.continuation_state.persistence:.3f}` (expected `{diag.continuation_state.expected_persistence:.3f}`)",
            f"- Follow-through: `{diag.continuation_state.followthrough:.3f}`",
            f"- Decay rate: `{diag.continuation_state.decay_rate:.3f}`",
            f"- Failure probability: `{diag.continuation_state.failure_probability:.3f}` ({diag.continuation_state.label})",
            "",
            "## Instability State",
            f"- Rolling std: `{diag.instability_state.rolling_std:.5f}`",
            f"- Entropy: `{diag.instability_state.entropy:.3f}`",
            f"- Directional coherence: `{diag.instability_state.directional_coherence:.3f}`",
            f"- Instability score: `{diag.instability_state.instability_score:.3f}` ({diag.instability_state.label})",
            "",
            "## Transition",
            f"- Previous: `{diag.transition_state.previous_label.value}` → Current: `{diag.transition_state.current_label.value}`",
            f"- Direction: `{diag.transition_state.direction}`  Probability: `{diag.transition_state.transition_probability:.3f}`",
            f"- Velocity: `{diag.transition_state.transition_velocity:.4f}`",
            "",
            "## Escalation Risk",
            f"- Short-term: `{diag.escalation_risk.short_term:.3f}`  Medium: `{diag.escalation_risk.medium_term:.3f}`  Long: `{diag.escalation_risk.long_term:.3f}`",
            f"- Direction bias: `{diag.escalation_risk.direction}`  Pressure build rate: `{diag.escalation_risk.pressure_build_rate:.3f}`",
            "",
            "## Causal Reasoning",
        ]
        for r in diag.causal_reasoning:
            lines.append(f"- {r}")
        if diag.gpt_interpretation:
            lines += ["", "## GPT Interpretation", diag.gpt_interpretation]
        if diag.diagnostic_summary:
            lines += ["", "## Summary", diag.diagnostic_summary]
        return "\n".join(lines)

    def build_dict(self, diag: StandardizedDiagnosis) -> Dict:
        return diag.to_dict()
