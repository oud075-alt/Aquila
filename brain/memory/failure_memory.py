"""Failure memory — records diagnoses whose expectations later failed.

The orchestrator can reference this memory to lower confidence when
similar patterns appear in the future. Storage is append-only JSON-lines
for simplicity and durability.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from brain.logging_utils import get_logger
from config import get_settings


class FailureMemory:
    def __init__(self, filename: str = "failures.jsonl"):
        settings = get_settings()
        self.log = get_logger("mspis.memory.failure")
        self.path: Path = settings.memory_dir / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def record(
        self,
        diagnosis_id: str,
        symbol: str,
        timeframe: str,
        original_label: str,
        actual_outcome: str,
        notes: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "ts": time.time(),
            "diagnosis_id": diagnosis_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "original_label": original_label,
            "actual_outcome": actual_outcome,
            "notes": notes,
            "extra": extra or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def by_symbol(self, symbol: str, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("symbol") != symbol:
                    continue
                if timeframe and obj.get("timeframe") != timeframe:
                    continue
                out.append(obj)
        return out

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not self.path.exists():
            return rows
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]
