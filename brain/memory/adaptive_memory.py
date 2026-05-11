"""Adaptive memory — bounded online learning for contradiction weighting.

The adaptive memory observes the outcome of past diagnoses (failure /
success of expectations) and slowly nudges the contradiction weights to
emphasise the dimensions that historically preceded confirmed pathologies.

Strict rules (per spec):
* Never self-modify core architecture.
* Never retrain on noise — updates are bounded and rate-limited.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict

from brain.logging_utils import get_logger
from brain.schemas import ContradictionScores
from config import get_market_config, get_settings


class AdaptiveMemory:
    def __init__(self, filename: str = "adaptive.json"):
        settings = get_settings()
        self.log = get_logger("mspis.memory.adaptive")
        self.path: Path = settings.memory_dir / filename
        self.cfg = get_market_config()
        self._state: Dict[str, Any] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "weight_offsets": {k: 0.0 for k in vars(self.cfg.contradiction_weights).keys()},
            "samples": 0,
            "last_updated": 0.0,
        }

    def _save(self) -> None:
        try:
            self.path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        except Exception as e:
            self.log.warning("adaptive save failed: %s", e)

    # ------------------------------------------------------------------
    # Update API
    # ------------------------------------------------------------------
    def reinforce(
        self,
        contradictions: ContradictionScores,
        confirmed_pathology: float,
        confidence: float,
        learning_rate: float = 0.005,
        cap: float = 0.30,
    ) -> Dict[str, float]:
        """Nudge weights toward features that fired before confirmed pathology.

        Updates are bounded (`|offset| <= cap`) and rate-limited
        (no more than one update per 5 seconds).
        """
        now = time.time()
        if now - float(self._state.get("last_updated", 0.0)) < 5.0:
            return self._state["weight_offsets"]

        cd = contradictions.as_dict()
        offsets: Dict[str, float] = self._state["weight_offsets"]
        signal = math.tanh(2.0 * confirmed_pathology - 1.0) * confidence
        for k, v in cd.items():
            current = offsets.get(k, 0.0)
            delta = learning_rate * signal * (v - 0.5)
            new = max(-cap, min(cap, current + delta))
            offsets[k] = float(new)
        self._state["weight_offsets"] = offsets
        self._state["samples"] = int(self._state.get("samples", 0)) + 1
        self._state["last_updated"] = now
        self._save()
        return offsets

    def offsets(self) -> Dict[str, float]:
        return dict(self._state.get("weight_offsets", {}))

    def stats(self) -> Dict[str, Any]:
        return {
            "samples": self._state.get("samples", 0),
            "last_updated": self._state.get("last_updated", 0.0),
            "weight_offsets": self.offsets(),
        }
