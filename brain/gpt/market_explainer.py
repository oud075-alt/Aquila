"""Market explainer — turns a diagnosis into a natural-language paragraph."""

from __future__ import annotations

from typing import Any, Dict

from brain.gpt.gpt_reasoning_bridge import GPTReasoningBridge
from brain.schemas import StandardizedDiagnosis


class MarketExplainer:
    def __init__(self, bridge: GPTReasoningBridge | None = None):
        self.bridge = bridge or GPTReasoningBridge()

    async def explain(self, diag: StandardizedDiagnosis) -> str:
        context = self._context(diag)
        prompt = (
            "Provide a concise but rigorous structural interpretation of the "
            "market state. Emphasise the dominant contradictions, what they "
            "imply about market physiology, and whether the structure is "
            "deteriorating, stabilising or releasing pressure."
        )
        return await self.bridge.interpret(prompt, context=context)

    def _context(self, diag: StandardizedDiagnosis) -> Dict[str, Any]:
        return {
            "symbol": diag.symbol,
            "timeframe": diag.timeframe,
            "exchange": diag.exchange,
            "market_state": diag.market_state.value,
            "severity": diag.severity.value,
            "regime": diag.regime.value,
            "pathology_scores": diag.pathology_scores.as_dict(),
            "contradiction_scores": diag.contradiction_scores.as_dict(),
            "volatility_state": diag.volatility_state.model_dump(),
            "liquidity_state": diag.liquidity_state.model_dump(),
            "continuation_state": diag.continuation_state.model_dump(),
            "instability_state": diag.instability_state.model_dump(),
            "transition_state": diag.transition_state.model_dump(),
            "escalation_risk": diag.escalation_risk.model_dump(),
            "structural_health": diag.structural_health.model_dump(),
            "causal_reasoning": diag.causal_reasoning,
            "confidence": diag.confidence_scores.overall_confidence,
        }
