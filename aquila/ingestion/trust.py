"""Per-source trust registry — closes audit gap #52."""

from __future__ import annotations

from aquila.core.numeric import safe_prob


class SourceTrustRegistry:
    def __init__(self) -> None:
        self._scores: dict[str, float] = {}

    def set(self, source_id: str, score: float) -> None:
        self._scores[source_id] = safe_prob(score)

    def get(self, source_id: str) -> float:
        return self._scores.get(source_id, 1.0)
