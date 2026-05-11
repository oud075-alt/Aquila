"""State transition engine.

Tracks the diagnosis label sequence per (symbol, timeframe) and inspects
the deterioration / recovery velocity between calls. Used to populate
:class:`StateTransition` on each diagnosis.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Tuple

from brain.math_core import clamp
from brain.schemas import DiagnosisLabel, SeverityLevel, StateTransition


@dataclass
class _History:
    labels: Deque[DiagnosisLabel]
    severities: Deque[int]
    timestamps: Deque[float]


class StateTransitionEngine:
    def __init__(self, history_size: int = 32):
        self.history_size = history_size
        self._store: Dict[Tuple[str, str], _History] = defaultdict(
            lambda: _History(
                labels=deque(maxlen=history_size),
                severities=deque(maxlen=history_size),
                timestamps=deque(maxlen=history_size),
            )
        )

    def update(
        self,
        symbol: str,
        timeframe: str,
        new_label: DiagnosisLabel,
        new_severity: SeverityLevel,
    ) -> StateTransition:
        key = (symbol, timeframe)
        hist = self._store[key]

        prev_label = hist.labels[-1] if hist.labels else DiagnosisLabel.UNDETERMINED
        prev_severity = hist.severities[-1] if hist.severities else 0
        now = time.time()
        prev_ts = hist.timestamps[-1] if hist.timestamps else now

        hist.labels.append(new_label)
        hist.severities.append(new_severity.level)
        hist.timestamps.append(now)

        if len(hist.severities) < 2:
            return StateTransition(
                previous_label=prev_label,
                current_label=new_label,
                transition_probability=0.0,
                transition_velocity=0.0,
                direction="STABLE",
                notes="No prior state.",
            )

        # Velocity: change in severity per second
        delta_severity = float(new_severity.level - prev_severity)
        dt = max(1.0, float(now - prev_ts))
        velocity = clamp(delta_severity / dt, -1.0, 1.0)

        # Probability of true transition: weight by label change + severity move
        label_changed = 1.0 if prev_label != new_label else 0.0
        severity_normalised = clamp(delta_severity / 5.0, -1.0, 1.0)
        prob = clamp(0.5 * label_changed + 0.5 * (abs(severity_normalised)), 0.0, 1.0)

        if delta_severity > 0:
            direction = "DEGRADING"
        elif delta_severity < 0:
            direction = "RECOVERING"
        else:
            direction = "STABLE" if not label_changed else "TRANSITION"

        notes = f"Severity {prev_severity} → {new_severity.level} over {dt:.1f}s"

        return StateTransition(
            previous_label=prev_label,
            current_label=new_label,
            transition_probability=prob,
            transition_velocity=velocity,
            direction=direction,
            notes=notes,
        )

    def history(self, symbol: str, timeframe: str) -> List[Dict]:
        key = (symbol, timeframe)
        hist = self._store.get(key)
        if not hist:
            return []
        out = []
        for ts, lab, sev in zip(hist.timestamps, hist.labels, hist.severities):
            out.append({"timestamp": ts, "label": lab.value, "severity": sev})
        return out
