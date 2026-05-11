"""Market history memory — durable parquet store of every diagnosis emitted."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from brain.logging_utils import get_logger
from brain.schemas import StandardizedDiagnosis
from config import get_settings

try:
    import pandas as pd
    import pyarrow  # noqa: F401 (parquet backend)
    _HAS_PARQUET = True
except Exception:
    pd = None  # type: ignore
    _HAS_PARQUET = False


class MarketHistoryMemory:
    """Persists diagnoses for later analysis / model adaptation."""

    def __init__(self, filename: str = "diagnoses.jsonl"):
        settings = get_settings()
        self.log = get_logger("mspis.memory.history")
        self.jsonl_path: Path = settings.memory_dir / filename
        self.parquet_path: Path = settings.memory_dir / "diagnoses.parquet"
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.jsonl_path.exists():
            self.jsonl_path.touch()

    def append(self, diag: StandardizedDiagnosis) -> None:
        row = self._flatten(diag)
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.jsonl_path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with self.jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]

    def export_parquet(self) -> Path:
        if not _HAS_PARQUET:
            raise RuntimeError("pandas/pyarrow not available")
        rows = self.recent(limit=10_000_000)
        if not rows:
            return self.parquet_path
        df = pd.DataFrame(rows)
        df.to_parquet(self.parquet_path, index=False)
        return self.parquet_path

    @staticmethod
    def _flatten(diag: StandardizedDiagnosis) -> Dict[str, Any]:
        d = diag.to_dict()
        return {
            "timestamp": d.get("timestamp"),
            "symbol": d.get("symbol"),
            "timeframe": d.get("timeframe"),
            "exchange": d.get("exchange"),
            "market_state": d.get("market_state"),
            "severity": d.get("severity"),
            "regime": d.get("regime"),
            "overall_pathology": diag.overall_pathology(),
            "pathology_scores": d.get("pathology_scores"),
            "contradiction_scores": d.get("contradiction_scores"),
            "confidence_scores": d.get("confidence_scores"),
            "escalation_risk": d.get("escalation_risk"),
            "structural_health": d.get("structural_health"),
            "transition_state": d.get("transition_state"),
            "diagnostic_summary": d.get("diagnostic_summary"),
        }
