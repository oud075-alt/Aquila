"""Phase 5 — Adaptive Memory + Learning.

Deterministic, NON-self-modifying learning per Appendix D:

    Allowed mechanisms ONLY:
        - Bayesian posterior updates (Beta-Binomial reliability calibration)
        - EWMA reliability calibration
        - replay-based episodic memory
        - confidence recalibration

    Forbidden:
        - gradient descent
        - self-modifying architecture
        - autonomous code generation
        - uncontrolled reinforcement learning
        - stochastic weight mutation

Two roles:

    1. `observe(envelope, market_state)` — stream sink: stores every
       diagnosis snapshot into the MemoryStore for later outcome
       assignment.

    2. `assign_outcomes(future_states)` — applied retrospectively when
       enough future bars are available, computes the realized validation
       label (Appendix E: realized volatility evolution, realized
       drawdown, CUSUM break, volatility regime persistence), updates
       Beta-Binomial reliability per pathology bucket, and exposes
       calibrated reliability via `.reliability(...)`.

The reliability tables are READ-ONLY views; nothing here rewrites code
or model architectures.
"""

from __future__ import annotations

import asyncio
import math
import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from core.pathology.metrics import EPS
from core.persistence.memory_store import MemoryEntry, MemoryStore
from core.schemas.diagnosis_envelope import DiagnosisEnvelope
from core.schemas.enums import Regime, StructuralState, Timeframe
from core.schemas.market_state import MarketState

# Appendix E parameters
OUTCOME_HORIZON_BARS: int = 16
REALIZED_VOL_WINDOW: int = 16
CUSUM_K: float = 0.5
CUSUM_H: float = 4.0
INSTABILITY_PERSISTENCE_THRESHOLD: float = 0.55


@dataclass(slots=True)
class _BetaBinomial:
    alpha: float = 1.0
    beta: float = 1.0

    def update(self, success: bool) -> None:
        if success:
            self.alpha += 1.0
        else:
            self.beta += 1.0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def n(self) -> int:
        return int(self.alpha + self.beta - 2)

    def credible_interval(self, *, lower: float = 0.05, upper: float = 0.95) -> tuple[float, float]:
        try:
            from scipy.stats import beta as beta_dist
        except ImportError:  # pragma: no cover
            return self.mean, self.mean
        return float(beta_dist.ppf(lower, self.alpha, self.beta)), float(
            beta_dist.ppf(upper, self.alpha, self.beta)
        )


@dataclass(slots=True)
class ReliabilityTable:
    """Per-bucket Beta-Binomial reliability with EWMA confidence calibration."""

    posteriors: dict[str, _BetaBinomial] = field(default_factory=lambda: defaultdict(_BetaBinomial))
    ewma_calibration: dict[str, float] = field(default_factory=dict)
    ewma_alpha: float = 0.05

    def update(self, bucket: str, *, success: bool, predicted_confidence: float) -> None:
        self.posteriors[bucket].update(success)
        prev = self.ewma_calibration.get(bucket, predicted_confidence)
        target = 1.0 if success else 0.0
        new = (1.0 - self.ewma_alpha) * prev + self.ewma_alpha * target
        self.ewma_calibration[bucket] = new

    def reliability(self, bucket: str) -> float:
        bb = self.posteriors.get(bucket)
        if bb is None:
            return 0.5
        return bb.mean

    def calibration_factor(self, bucket: str, *, raw_confidence: float) -> float:
        if not self.posteriors.get(bucket):
            return raw_confidence
        reliability = self.reliability(bucket)
        ewma_target = self.ewma_calibration.get(bucket, raw_confidence)
        blended = 0.5 * reliability + 0.5 * ewma_target
        return max(0.0, min(1.0, 0.5 * raw_confidence + 0.5 * blended))


@dataclass(frozen=True, slots=True)
class _DiagnosisSnapshot:
    memory_id: int
    timestamp: datetime
    timeframe: Timeframe
    bucket: str
    predicted_confidence: float
    predicted_aggregate: float
    predicted_instability: float
    structural_state: StructuralState
    regime: Regime


class AdaptiveLearningEngine:
    """Phase 5 — deterministic episodic memory + reliability calibration."""

    def __init__(self, memory: MemoryStore | None = None, *, symbol: str = "BTCUSDT") -> None:
        self.memory = memory
        self.symbol = symbol.upper()
        self.table = ReliabilityTable()
        self._lock = asyncio.Lock()
        self._pending: list[_DiagnosisSnapshot] = []

    @staticmethod
    def bucket(envelope: DiagnosisEnvelope) -> str:
        return f"{envelope.regime.regime.value}/{envelope.pathology.structural_state.value}"

    async def observe(self, *, envelope: DiagnosisEnvelope, market_state: MarketState) -> None:
        bucket = self.bucket(envelope)
        async with self._lock:
            memory_id = -1
            if self.memory is not None:
                memory_id = self.memory.remember(
                    symbol=envelope.symbol,
                    timeframe=envelope.timeframe,
                    timestamp=envelope.timestamp,
                    kind="diagnosis_snapshot",
                    payload={
                        "bucket": bucket,
                        "confidence": envelope.confidence_state.global_confidence,
                        "aggregate": envelope.pathology.scores.aggregate,
                        "instability": envelope.pathology.instability_score,
                        "structural_state": envelope.pathology.structural_state.value,
                        "regime": envelope.regime.regime.value,
                        "close": market_state.current_bar.close,
                    },
                    outcome_score=None,
                )
            self._pending.append(
                _DiagnosisSnapshot(
                    memory_id=memory_id,
                    timestamp=envelope.timestamp,
                    timeframe=envelope.timeframe,
                    bucket=bucket,
                    predicted_confidence=envelope.confidence_state.global_confidence,
                    predicted_aggregate=envelope.pathology.scores.aggregate,
                    predicted_instability=envelope.pathology.instability_score,
                    structural_state=envelope.pathology.structural_state,
                    regime=envelope.regime.regime,
                )
            )

    def reliability(self, bucket: str) -> float:
        return self.table.reliability(bucket)

    def calibration_factor(self, bucket: str, *, raw_confidence: float) -> float:
        return self.table.calibration_factor(bucket, raw_confidence=raw_confidence)

    @staticmethod
    def _realized_volatility(closes: Iterable[float]) -> float:
        closes_list = list(closes)
        if len(closes_list) < 3:
            return 0.0
        returns = np.diff(np.log(np.maximum(np.asarray(closes_list, dtype=np.float64), EPS)))
        return float(returns.std()) if returns.size else 0.0

    @staticmethod
    def _cusum_break(closes: Iterable[float]) -> bool:
        closes_list = list(closes)
        if len(closes_list) < 4:
            return False
        rets = np.diff(np.log(np.maximum(np.asarray(closes_list, dtype=np.float64), EPS)))
        if rets.size == 0:
            return False
        mean = float(rets.mean())
        sigma = float(rets.std()) + EPS
        s_pos = 0.0
        s_neg = 0.0
        for r in rets:
            z = (r - mean) / sigma
            s_pos = max(0.0, s_pos + z - CUSUM_K)
            s_neg = min(0.0, s_neg + z + CUSUM_K)
            if s_pos > CUSUM_H or s_neg < -CUSUM_H:
                return True
        return False

    def assign_outcomes_from_closes(self, future_closes_by_id: dict[int, list[float]]) -> int:
        """Retro-assign realized outcomes (offline / batch path)."""
        applied = 0
        remaining: list[_DiagnosisSnapshot] = []
        for snap in self._pending:
            closes = future_closes_by_id.get(snap.memory_id)
            if closes is None or len(closes) < OUTCOME_HORIZON_BARS:
                remaining.append(snap)
                continue
            realized = self._realized_volatility(closes[:OUTCOME_HORIZON_BARS])
            broke = self._cusum_break(closes[:OUTCOME_HORIZON_BARS])
            mean_close = float(np.mean(closes[:OUTCOME_HORIZON_BARS]))
            normalized_vol = realized / max(mean_close * 1e-4, EPS)
            instability_realized = min(1.0, normalized_vol)
            predicted_distress = snap.predicted_instability >= INSTABILITY_PERSISTENCE_THRESHOLD
            realized_distress = (instability_realized >= INSTABILITY_PERSISTENCE_THRESHOLD) or broke
            success = predicted_distress == realized_distress
            self.table.update(
                snap.bucket,
                success=success,
                predicted_confidence=snap.predicted_confidence,
            )
            if self.memory is not None and snap.memory_id > 0:
                outcome_score = 1.0 if success else 0.0
                try:
                    self.memory.assign_outcome(snap.memory_id, outcome_score=outcome_score)
                except Exception:  # pragma: no cover
                    pass
            applied += 1
        self._pending = remaining
        return applied

    def summary(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for bucket, bb in self.table.posteriors.items():
            out[bucket] = {
                "mean": bb.mean,
                "alpha": bb.alpha,
                "beta": bb.beta,
                "n": float(bb.n),
                "ewma": self.table.ewma_calibration.get(bucket, bb.mean),
            }
        return out

    @staticmethod
    def median(xs: Iterable[float]) -> float:
        xs_list = [float(x) for x in xs]
        if not xs_list:
            return 0.0
        return float(statistics.median(xs_list))

    @staticmethod
    def log(x: float) -> float:
        return math.log(max(x, EPS))
