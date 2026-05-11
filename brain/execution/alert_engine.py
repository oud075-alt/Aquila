"""Alert engine.

Emits structural alerts when severity crosses configurable thresholds or
when state transitions cross priority lines. Alerts are stored as JSONL
records and also pushed to async listeners (e.g. websocket fan-out).
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

from brain.logging_utils import get_logger
from brain.schemas import SeverityLevel, StandardizedDiagnosis
from config import get_settings


_DEFAULT_THRESHOLDS = {
    SeverityLevel.MINOR_INSTABILITY: 0.40,
    SeverityLevel.FRAGILE_STRUCTURE: 0.55,
    SeverityLevel.HIGH_RISK_TRANSITION: 0.70,
    SeverityLevel.PRE_COLLAPSE: 0.82,
    SeverityLevel.STRUCTURAL_FAILURE: 0.92,
}


class AlertEngine:
    def __init__(self):
        settings = get_settings()
        self.log = get_logger("mspis.execution.alert")
        self.path: Path = settings.data_dir / "alerts.jsonl"
        if not self.path.exists():
            self.path.touch()
        self._listeners: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []

    def add_listener(self, fn: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        self._listeners.append(fn)

    async def evaluate(self, diag: StandardizedDiagnosis) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        aggregate = diag.overall_pathology()
        severity_level = diag.severity

        threshold = _DEFAULT_THRESHOLDS.get(severity_level, 1.1)
        if aggregate >= threshold:
            alerts.append(self._make("AGGREGATE_THRESHOLD", diag, aggregate, threshold))

        # Stress + liquidity tandem alert
        if (
            diag.pathology_scores.stress_escalation >= 0.65
            and diag.pathology_scores.liquidity_fragility >= 0.60
        ):
            alerts.append(self._make(
                "STRESS_PLUS_LIQUIDITY_FRAGILITY", diag,
                value=(diag.pathology_scores.stress_escalation + diag.pathology_scores.liquidity_fragility) / 2,
                threshold=0.625,
            ))

        # Pre-collapse alert
        if diag.pathology_scores.pre_collapse >= 0.65:
            alerts.append(self._make(
                "PRE_COLLAPSE_PROBABILITY", diag,
                value=diag.pathology_scores.pre_collapse, threshold=0.65,
            ))

        # Transition degradation alert
        if diag.transition_state.direction == "DEGRADING" and diag.transition_state.transition_probability >= 0.5:
            alerts.append(self._make(
                "STRUCTURAL_DEGRADATION_TRANSITION", diag,
                value=diag.transition_state.transition_probability, threshold=0.5,
            ))

        for a in alerts:
            self._persist(a)
            await self._broadcast(a)
        return alerts

    # ------------------------------------------------------------------
    def _make(self, kind: str, diag: StandardizedDiagnosis, value: float, threshold: float) -> Dict[str, Any]:
        return {
            "ts": time.time(),
            "kind": kind,
            "symbol": diag.symbol,
            "timeframe": diag.timeframe,
            "exchange": diag.exchange,
            "label": diag.market_state.value,
            "severity": diag.severity.value,
            "value": float(value),
            "threshold": float(threshold),
            "diagnostic_summary": diag.diagnostic_summary,
        }

    def _persist(self, alert: Dict[str, Any]) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(alert) + "\n")
        except Exception as e:
            self.log.warning("alert persist failed: %s", e)

    async def _broadcast(self, alert: Dict[str, Any]) -> None:
        for fn in list(self._listeners):
            try:
                await fn(alert)
            except Exception as e:
                self.log.debug("alert listener error: %s", e)

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out[-limit:]
