"""Diagnostic summary AI.

Produces a multi-paragraph diagnostic report (suitable for inclusion in the
report generator) by orchestrating two GPT calls: a structural reasoning
pass and a pathology-evolution pass. Fully degrades to deterministic
templates when no GPT is available.
"""

from __future__ import annotations

from typing import Any, Dict, List

from brain.gpt.gpt_reasoning_bridge import GPTReasoningBridge
from brain.schemas import StandardizedDiagnosis


class DiagnosticSummaryAI:
    def __init__(self, bridge: GPTReasoningBridge | None = None):
        self.bridge = bridge or GPTReasoningBridge()

    async def summarise(self, diag: StandardizedDiagnosis) -> Dict[str, str]:
        ctx = self._context(diag)
        reasoning = await self.bridge.interpret(
            (
                "Explain the internal structural pathology of this market state. "
                "Highlight the top contradictions and the most likely structural "
                "weakness that could produce escalation. Do not include trade ideas."
            ),
            context=ctx,
        )
        evolution = await self.bridge.interpret(
            (
                "Based on the transition state and escalation risk, describe how "
                "the structure is evolving (degrading, recovering, stable) and "
                "what the most probable next pathology phase would look like. "
                "Stay strictly diagnostic."
            ),
            context=ctx,
        )
        return {"reasoning": reasoning, "evolution": evolution}

    def _context(self, diag: StandardizedDiagnosis) -> Dict[str, Any]:
        return {
            "symbol": diag.symbol,
            "timeframe": diag.timeframe,
            "market_state": diag.market_state.value,
            "severity": diag.severity.value,
            "regime": diag.regime.value,
            "pathology_scores": diag.pathology_scores.as_dict(),
            "contradiction_scores": diag.contradiction_scores.as_dict(),
            "escalation_risk": diag.escalation_risk.model_dump(),
            "transition_state": diag.transition_state.model_dump(),
            "structural_health": diag.structural_health.model_dump(),
            "confidence": diag.confidence_scores.overall_confidence,
            "causal_reasoning": diag.causal_reasoning,
        }
