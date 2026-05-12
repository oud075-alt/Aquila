"""M1F — Continuation decay primitive (Appendix M1F + V).

continuation_decay = uniform-weighted combination of:
    - momentum_decay        := 1 - rolling momentum persistence
    - autocorrelation_breakdown (reused primitive)
    - directional_efficiency_collapse := 1 - directional_efficiency

Window = 32 bars. Uniform weights per Appendix V (M1F: 1/3 each).
"""

from __future__ import annotations

import numpy as np

from core.pathology.autocorrelation_breakdown import AutocorrelationBreakdown
from core.pathology.metrics import clip01, directional_efficiency
from core.schemas.market_state import MarketState

WINDOW: int = 32

W_MOMENTUM: float = 1.0 / 3.0
W_AUTOCORR: float = 1.0 / 3.0
W_DIRECTIONAL: float = 1.0 / 3.0


class ContinuationDecay:
    """Directional persistence deterioration score."""

    def __init__(self, ac_breakdown: AutocorrelationBreakdown | None = None) -> None:
        self.ac = ac_breakdown or AutocorrelationBreakdown()

    def _momentum_persistence(self, closes: np.ndarray) -> float:
        if len(closes) < WINDOW + 2:
            return 0.0
        seg = closes[-(WINDOW + 1) :]
        signs = np.sign(np.diff(seg))
        if len(signs) <= 1:
            return 0.0
        agree = float(np.mean(signs[:-1] == signs[1:]))
        return agree

    def compute(self, state: MarketState) -> float:
        closes = np.array(state.closes, dtype=np.float64)
        if len(closes) < WINDOW + 2:
            return 0.0
        momentum_persistence = self._momentum_persistence(closes)
        momentum_decay = clip01(1.0 - momentum_persistence)
        ac_break = self.ac.compute(state)
        de = directional_efficiency(closes, window=WINDOW)
        directional_collapse = clip01(1.0 - de)
        combined = (
            W_MOMENTUM * momentum_decay
            + W_AUTOCORR * ac_break
            + W_DIRECTIONAL * directional_collapse
        )
        return clip01(combined)
