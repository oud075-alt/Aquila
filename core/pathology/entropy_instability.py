"""M1A — Entropy instability primitive (Appendix M1A).

Rolling Shannon entropy over the sequence of structural-state labels
emitted by the StructuralStateClassifier. Window = 64 bars. Normalized
by log2(|alphabet|) so output ∈ [0,1].
"""

from __future__ import annotations

import math
from collections import Counter

from core.pathology.structural_state_classifier import StructuralStateClassifier
from core.schemas.enums import StructuralState
from core.schemas.market_state import MarketState

ENTROPY_WINDOW: int = 64
_ALPHABET_SIZE: int = len(StructuralState)
_LOG2_ALPHABET: float = math.log2(_ALPHABET_SIZE)


class EntropyInstability:
    """Compute normalized Shannon entropy of structural-state transitions."""

    def __init__(self, classifier: StructuralStateClassifier | None = None) -> None:
        self.classifier = classifier or StructuralStateClassifier()

    def compute(self, state: MarketState) -> tuple[float, list[StructuralState]]:
        window = state.window[-ENTROPY_WINDOW:]
        labels = self.classifier.classify_window(window)
        if not labels:
            return 0.0, []
        counts = Counter(labels)
        total = float(len(labels))
        entropy = 0.0
        for n in counts.values():
            p = n / total
            if p > 0:
                entropy -= p * math.log2(p)
        normalized = entropy / _LOG2_ALPHABET if _LOG2_ALPHABET > 0 else 0.0
        if normalized < 0.0:
            normalized = 0.0
        if normalized > 1.0:
            normalized = 1.0
        return normalized, labels
