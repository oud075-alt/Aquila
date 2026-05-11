"""Adaptive calibration logic — slowly drifting thresholds.

Bounded: thresholds remain in a fixed admissible range. This is NOT
reinforcement learning; it is statistical re-centering on an EWMA. The
update is deterministic given the input sequence, satisfying replay.
"""

from __future__ import annotations


class AdaptiveCalibrator:
    def __init__(
        self,
        initial_low: float = 0.005,
        initial_high: float = 0.02,
        alpha: float = 0.05,
        min_low: float = 0.001,
        max_high: float = 0.10,
    ) -> None:
        self.low = initial_low
        self.high = initial_high
        self.alpha = alpha
        self.min_low = min_low
        self.max_high = max_high
        self._ewma_vol: float | None = None

    def observe(self, realized_vol: float) -> None:
        if realized_vol < 0 or realized_vol != realized_vol:  # NaN check
            return
        if self._ewma_vol is None:
            self._ewma_vol = realized_vol
        else:
            self._ewma_vol = (1 - self.alpha) * self._ewma_vol + self.alpha * realized_vol
        # gently re-center thresholds
        if self._ewma_vol is not None:
            target_low = max(self.min_low, self._ewma_vol * 0.4)
            target_high = min(self.max_high, self._ewma_vol * 2.0)
            self.low = (1 - self.alpha) * self.low + self.alpha * target_low
            self.high = (1 - self.alpha) * self.high + self.alpha * target_high

    def delta(self) -> float:
        return self.high - self.low
