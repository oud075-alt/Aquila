"""GPT reasoning bridge.

Thin async wrapper around the OpenAI Chat Completions API. The bridge:

* enforces the diagnostic-only system prompt (never produces trade signals);
* gracefully falls back to a deterministic textual summariser when the
  API key is missing or the API call fails — guaranteeing the diagnosis
  pipeline always has *some* natural-language interpretation.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from brain.logging_utils import get_logger
from config import get_api_keys, get_settings

try:
    from openai import OpenAI  # type: ignore
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False
    OpenAI = None  # type: ignore


_SYSTEM_PROMPT = (
    "You are MSPIS — a market structural pathologist. Your job is to "
    "INTERPRET diagnostic findings about market structural health. "
    "You never produce trade signals, entries, exits, take-profits, or "
    "stop-losses. You never categorise the market as 'bullish/bearish/sideway'. "
    "You think like a pathologist diagnosing internal disease. You explain "
    "structural contradictions, hidden exhaustion, instability escalation, "
    "liquidity fragility, acceptance failure, manipulation footprints, and "
    "pre-collapse / pre-expansion compression. Provide clear, calibrated, "
    "evidence-based explanations using the data provided. If evidence is "
    "weak, state so explicitly. Output plain prose, no markdown headings."
)


class GPTReasoningBridge:
    def __init__(self):
        self.log = get_logger("mspis.gpt.bridge")
        self.settings = get_settings()
        self.keys = get_api_keys()
        self._client = None
        if _HAS_OPENAI and self.keys.has_openai():
            try:
                self._client = OpenAI(api_key=self.keys.openai_api_key)
                self.log.info("OpenAI client initialised (model=%s)", self.settings.openai_model)
            except Exception as e:
                self.log.warning("OpenAI init failed: %s", e)
                self._client = None
        else:
            self.log.info("OpenAI not configured — using deterministic fallback")

    @property
    def available(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------
    async def interpret(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        if self._client is None:
            return self._fallback(prompt, context)
        loop = asyncio.get_running_loop()
        try:
            text = await loop.run_in_executor(None, self._call_openai, prompt, context)
            return text or self._fallback(prompt, context)
        except Exception as e:
            self.log.warning("OpenAI call failed (%s); falling back", e)
            return self._fallback(prompt, context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _call_openai(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        assert self._client is not None
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        if context:
            messages.append({
                "role": "user",
                "content": f"Diagnostic context (JSON):\n{context}\n\nQuestion: {prompt}",
            })
        else:
            messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=float(self.settings.openai_temperature),
            max_tokens=int(self.settings.openai_max_tokens),
            messages=messages,
        )
        return (resp.choices[0].message.content or "").strip()

    # ------------------------------------------------------------------
    # Deterministic fallback
    # ------------------------------------------------------------------
    def _fallback(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        ctx = context or {}
        label = ctx.get("market_state") or "UNDETERMINED"
        severity = ctx.get("severity") or "LEVEL_0_HEALTHY_STRUCTURE"
        scores = ctx.get("pathology_scores") or {}
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:4]
        contradictions = ctx.get("contradiction_scores") or {}
        top_contradiction = max(contradictions.items(), key=lambda kv: kv[1], default=("none", 0.0))
        causal = ctx.get("causal_reasoning") or []

        parts = [
            f"Structural diagnosis: {label} (severity={severity}).",
        ]
        if ranked:
            top_str = ", ".join(f"{k}={v:.2f}" for k, v in ranked)
            parts.append(f"Dominant pathology contributors: {top_str}.")
        if top_contradiction[1] > 0.0:
            parts.append(
                f"Most pronounced contradiction: {top_contradiction[0]} = {top_contradiction[1]:.2f}."
            )
        if causal:
            parts.append("Causal evidence: " + " | ".join(causal[:4]))
        parts.append(
            "This interpretation is purely structural — it does not contain "
            "any trade signals or directional recommendations."
        )
        return " ".join(parts)
