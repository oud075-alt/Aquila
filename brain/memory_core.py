"""Memory core — coordinator across every memory subsystem.

Provides a single entry point for the orchestrator. Each call records a
diagnosis into vector / pattern / history memories and updates the
adaptive memory with bounded learning.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List

from brain.logging_utils import get_logger
from brain.memory.adaptive_memory import AdaptiveMemory
from brain.memory.failure_memory import FailureMemory
from brain.memory.market_history_memory import MarketHistoryMemory
from brain.memory.pattern_memory import PatternMemory
from brain.memory.vector_memory import VectorMemory
from brain.schemas import StandardizedDiagnosis


class MemoryCore:
    def __init__(self):
        self.log = get_logger("mspis.memory.core")
        self.vector = VectorMemory()
        self.pattern = PatternMemory()
        self.failure = FailureMemory()
        self.history = MarketHistoryMemory()
        self.adaptive = AdaptiveMemory()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def absorb(self, diag: StandardizedDiagnosis) -> Dict[str, Any]:
        diag_id = self._diagnosis_id(diag)

        # 1. Append to durable history.
        try:
            self.history.append(diag)
        except Exception as e:
            self.log.warning("history append failed: %s", e)

        # 2. Vector memory — semantic search for similar past states.
        text = self._to_text(diag)
        metadata = {
            "diagnosis_id": diag_id,
            "symbol": diag.symbol,
            "timeframe": diag.timeframe,
            "label": diag.market_state.value,
            "severity": diag.severity.value,
            "pathology_aggregate": diag.overall_pathology(),
            "ts": time.time(),
        }
        try:
            self.vector.store(diag_id, text, metadata)
        except Exception as e:
            self.log.warning("vector store failed: %s", e)

        # 3. Pattern memory — fingerprint of pathology distribution.
        try:
            signature = self._signature(diag)
            self.pattern.record(
                signature=signature,
                label=diag.market_state.value,
                severity=diag.severity.value,
                symbol=diag.symbol,
                timeframe=diag.timeframe,
                extra={"aggregate": diag.overall_pathology()},
            )
        except Exception as e:
            self.log.warning("pattern record failed: %s", e)

        # 4. Adaptive memory — bounded reinforcement.
        try:
            self.adaptive.reinforce(
                contradictions=diag.contradiction_scores,
                confirmed_pathology=diag.overall_pathology(),
                confidence=diag.confidence_scores.overall_confidence,
            )
        except Exception as e:
            self.log.warning("adaptive reinforce failed: %s", e)

        return {"diagnosis_id": diag_id, "stored_at": time.time()}

    # ------------------------------------------------------------------
    # Failure feedback
    # ------------------------------------------------------------------
    def record_failure(
        self,
        diagnosis_id: str,
        diag: StandardizedDiagnosis,
        actual_outcome: str,
        notes: str | None = None,
    ) -> None:
        self.failure.record(
            diagnosis_id=diagnosis_id,
            symbol=diag.symbol,
            timeframe=diag.timeframe,
            original_label=diag.market_state.value,
            actual_outcome=actual_outcome,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def similar_past(self, diag: StandardizedDiagnosis, k: int = 5) -> List[Dict[str, Any]]:
        text = self._to_text(diag)
        return self.vector.search(text, k=k)

    def recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.history.recent(limit=limit)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _diagnosis_id(diag: StandardizedDiagnosis) -> str:
        raw = f"{diag.symbol}|{diag.timeframe}|{diag.timestamp.isoformat()}|{diag.market_state.value}"
        return hashlib.sha1(raw.encode()).hexdigest()

    @staticmethod
    def _to_text(diag: StandardizedDiagnosis) -> str:
        ps = " ".join(f"{k}:{v:.2f}" for k, v in diag.pathology_scores.as_dict().items())
        cs = " ".join(f"{k}:{v:.2f}" for k, v in diag.contradiction_scores.as_dict().items())
        return (
            f"symbol={diag.symbol} timeframe={diag.timeframe} regime={diag.regime.value} "
            f"label={diag.market_state.value} severity={diag.severity.value} "
            f"pathology=[{ps}] contradictions=[{cs}]"
        )

    @staticmethod
    def _signature(diag: StandardizedDiagnosis) -> List[float]:
        ps = list(diag.pathology_scores.as_dict().values())
        cs = list(diag.contradiction_scores.as_dict().values())
        extras = [
            diag.volatility_state.realized_vol,
            diag.volatility_state.expected_vol,
            diag.volatility_state.vol_of_vol,
            diag.liquidity_state.fragility_score,
            diag.continuation_state.failure_probability,
            diag.instability_state.instability_score,
        ]
        return [float(x) for x in (ps + cs + extras)]
