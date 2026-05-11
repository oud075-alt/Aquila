"""Pattern memory — persistent record of structural signatures.

Stores fingerprints (compact feature vectors) of past structural states
together with the diagnosis they produced. Used by the adaptive memory
layer to recognise recurring pathology signatures.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from brain.logging_utils import get_logger
from config import get_settings


class PatternMemory:
    def __init__(self, filename: str = "patterns.jsonl"):
        settings = get_settings()
        self.log = get_logger("mspis.memory.pattern")
        self.path: Path = settings.memory_dir / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def record(
        self,
        signature: List[float],
        label: str,
        severity: str,
        symbol: str,
        timeframe: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "ts": time.time(),
            "symbol": symbol,
            "timeframe": timeframe,
            "label": label,
            "severity": severity,
            "signature": [float(x) for x in signature],
            "extra": extra or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def closest(self, signature: List[float], k: int = 5) -> List[Dict[str, Any]]:
        target = np.asarray(signature, dtype=np.float64)
        n = float(np.linalg.norm(target)) or 1.0
        records = self.all()
        scored: List[Dict[str, Any]] = []
        for r in records:
            sig = np.asarray(r.get("signature", []), dtype=np.float64)
            if sig.size != target.size:
                continue
            m = float(np.linalg.norm(sig)) or 1.0
            sim = float(np.dot(sig, target) / (n * m))
            scored.append(r | {"similarity": sim})
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:k]
