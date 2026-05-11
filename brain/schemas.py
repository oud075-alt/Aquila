"""Standardized intelligence schemas.

Every module in MSPIS consumes and produces the dataclasses defined below.
This enforces module interaction rules and guarantees that the diagnostic
flow is uniform across the system.

The :class:`StandardizedDiagnosis` is the canonical output object the
orchestrator produces and the API surfaces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class SeverityLevel(str, Enum):
    """Pathology severity hierarchy (LEVEL 0 … LEVEL 5)."""

    HEALTHY_STRUCTURE = "LEVEL_0_HEALTHY_STRUCTURE"
    MINOR_INSTABILITY = "LEVEL_1_MINOR_INSTABILITY"
    FRAGILE_STRUCTURE = "LEVEL_2_FRAGILE_STRUCTURE"
    HIGH_RISK_TRANSITION = "LEVEL_3_HIGH_RISK_TRANSITION"
    PRE_COLLAPSE = "LEVEL_4_PRE_COLLAPSE"
    STRUCTURAL_FAILURE = "LEVEL_5_STRUCTURAL_FAILURE"

    @property
    def level(self) -> int:
        return int(self.value.split("_")[1])


class DiagnosisLabel(str, Enum):
    """Top-level disease class assigned to the market state."""

    HEALTHY_EXPANSION = "HEALTHY_EXPANSION"
    HEALTHY_TREND = "HEALTHY_TREND"
    HEALTHY_COMPRESSION = "HEALTHY_COMPRESSION"
    FRAGILE_BREAKOUT = "FRAGILE_BREAKOUT"
    UNSTABLE_EXPANSION = "UNSTABLE_EXPANSION"
    STRUCTURAL_EXHAUSTION = "STRUCTURAL_EXHAUSTION"
    HIDDEN_DISTRIBUTION = "HIDDEN_DISTRIBUTION"
    MANIPULATIVE_ENVIRONMENT = "MANIPULATIVE_ENVIRONMENT"
    LIQUIDITY_STRESS_BUILDUP = "LIQUIDITY_STRESS_BUILDUP"
    PRE_COLLAPSE = "PRE_COLLAPSE"
    PRE_EXPANSION_COMPRESSION = "PRE_EXPANSION_COMPRESSION"
    CHAOTIC_TRANSITION = "CHAOTIC_TRANSITION"
    UNDETERMINED = "UNDETERMINED"


class RegimeLabel(str, Enum):
    """Coarse regime identification used by the regime model."""

    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"
    MEAN_REVERSION = "MEAN_REVERSION"
    CHAOTIC = "CHAOTIC"


# ---------------------------------------------------------------------------
# Market data primitives
# ---------------------------------------------------------------------------
class Candle(BaseModel):
    """A single OHLCV bar.

    All timestamps are timezone-aware (UTC). The structure is intentionally
    minimal so it can be produced by every supported data source.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None
    trades: Optional[int] = None

    @property
    def range(self) -> float:
        return float(self.high - self.low)

    @property
    def body(self) -> float:
        return float(abs(self.close - self.open))

    @property
    def upper_wick(self) -> float:
        return float(self.high - max(self.open, self.close))

    @property
    def lower_wick(self) -> float:
        return float(min(self.open, self.close) - self.low)

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open


class MarketSnapshot(BaseModel):
    """Container for everything the orchestrator needs for one diagnosis run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    symbol: str
    timeframe: str
    exchange: str = "synthetic"
    candles: List[Candle] = Field(default_factory=list)
    last_price: Optional[float] = None
    ticks: List[Dict[str, Any]] = Field(default_factory=list)
    orderbook_imbalance: Optional[float] = None
    news_events: List[Dict[str, Any]] = Field(default_factory=list)
    economic_events: List[Dict[str, Any]] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_valid(self, min_bars: int = 50) -> bool:
        return len(self.candles) >= min_bars


# ---------------------------------------------------------------------------
# Expectation profile (what SHOULD happen if market is healthy)
# ---------------------------------------------------------------------------
class ExpectationProfile(BaseModel):
    """The expected behaviour of a healthy market in current regime."""

    regime: RegimeLabel
    expected_trend_slope: float = 0.0
    expected_continuation_persistence: float = 0.0   # in [0,1]
    expected_volatility: float = 0.0
    expected_atr: float = 0.0
    expected_participation: float = 0.0              # expected normalised volume
    expected_acceptance: float = 0.0                 # in [0,1]
    expected_efficiency: float = 0.0                 # close-to-open / total path
    expected_breakout_followthrough: float = 0.0     # in [0,1]
    expected_pullback_depth: float = 0.0
    expected_compression_release_ratio: float = 0.0
    regime_confidence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Actual observed behaviour
# ---------------------------------------------------------------------------
class ActualBehaviorProfile(BaseModel):
    """Empirically measured behaviour from the latest market data."""

    realized_trend_slope: float = 0.0
    realized_continuation_persistence: float = 0.0
    realized_volatility: float = 0.0
    realized_atr: float = 0.0
    realized_participation: float = 0.0
    realized_acceptance: float = 0.0
    realized_efficiency: float = 0.0
    realized_breakout_followthrough: float = 0.0
    realized_pullback_depth: float = 0.0
    realized_compression_release_ratio: float = 0.0
    wick_body_ratio: float = 0.0
    rejection_intensity: float = 0.0
    momentum_persistence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Sub-scores
# ---------------------------------------------------------------------------
class PathologyScores(BaseModel):
    """All individual pathology probabilities, each in [0, 1]."""

    hidden_exhaustion: float = 0.0
    structural_instability: float = 0.0
    continuation_failure: float = 0.0
    liquidity_fragility: float = 0.0
    stress_escalation: float = 0.0
    acceptance_failure: float = 0.0
    behavioral_divergence: float = 0.0
    pre_collapse: float = 0.0
    compression_pressure: float = 0.0
    manipulation_footprint: float = 0.0
    entropy_disorder: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return self.model_dump()

    def aggregate(self) -> float:
        """Calibrated aggregate pathology score in [0,1].

        Combines three signals:
          * the maximum pathology probability (worst single signal)
          * the average of the top-3 pathologies (does any cluster fire?)
          * an attenuated probability-OR fusion (does many+ moderate signals fire?)

        The independent-event probability-OR formula 1 - Π(1 - p_i)
        saturates too quickly with 11 components and is therefore only
        used as a soft prior here.
        """
        values = sorted([max(0.0, min(1.0, float(v))) for v in self.as_dict().values()], reverse=True)
        if not values:
            return 0.0
        max_p = values[0]
        topk = values[: min(3, len(values))]
        topk_mean = sum(topk) / len(topk)
        # Attenuated probability-OR (root) so it doesn't saturate
        prob = 1.0
        for v in values:
            prob *= (1.0 - v)
        prob_or = 1.0 - prob
        prob_or_att = prob_or ** 1.6  # attenuate saturation
        return float(max(0.0, min(1.0, 0.45 * max_p + 0.35 * topk_mean + 0.20 * prob_or_att)))

    def max_score(self) -> float:
        return max(self.as_dict().values()) if self.as_dict() else 0.0


class ContradictionScores(BaseModel):
    """Magnitude of contradictions between expectation and observation."""

    momentum_vs_price: float = 0.0
    volume_vs_price: float = 0.0
    volatility_vs_continuation: float = 0.0
    range_vs_acceptance: float = 0.0
    breadth_vs_expansion: float = 0.0
    liquidity_vs_move: float = 0.0
    wick_vs_body: float = 0.0
    entropy_vs_direction: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return self.model_dump()


class VolatilityState(BaseModel):
    realized_vol: float = 0.0
    expected_vol: float = 0.0
    vol_of_vol: float = 0.0
    compression_ratio: float = 0.0
    expansion_ratio: float = 0.0
    label: str = "UNKNOWN"


class LiquidityState(BaseModel):
    participation: float = 0.0
    expected_participation: float = 0.0
    imbalance: float = 0.0
    sweep_frequency: float = 0.0
    fragility_score: float = 0.0
    label: str = "UNKNOWN"


class ContinuationState(BaseModel):
    persistence: float = 0.0
    expected_persistence: float = 0.0
    followthrough: float = 0.0
    decay_rate: float = 0.0
    failure_probability: float = 0.0
    label: str = "UNKNOWN"


class InstabilityState(BaseModel):
    rolling_std: float = 0.0
    entropy: float = 0.0
    directional_coherence: float = 0.0
    instability_score: float = 0.0
    label: str = "UNKNOWN"


class ConfidenceScores(BaseModel):
    sample_size_score: float = 0.0
    signal_quality_score: float = 0.0
    contradiction_consistency: float = 0.0
    noise_score: float = 0.0
    overall_confidence: float = 0.0


# ---------------------------------------------------------------------------
# State transition & escalation
# ---------------------------------------------------------------------------
class StateTransition(BaseModel):
    previous_label: DiagnosisLabel = DiagnosisLabel.UNDETERMINED
    current_label: DiagnosisLabel = DiagnosisLabel.UNDETERMINED
    transition_probability: float = 0.0
    transition_velocity: float = 0.0
    direction: str = "STABLE"  # STABLE | DEGRADING | RECOVERING
    notes: str = ""


class EscalationRisk(BaseModel):
    short_term: float = 0.0   # ~1-5 bars
    medium_term: float = 0.0  # ~10-30 bars
    long_term: float = 0.0    # ~50+ bars
    direction: str = "NEUTRAL"   # COLLAPSE_BIAS | EXPANSION_BIAS | NEUTRAL
    pressure_build_rate: float = 0.0


class StructuralHealth(BaseModel):
    score: float = 1.0
    physiology_alignment: float = 1.0
    deterioration_velocity: float = 0.0
    summary: str = "healthy"


# ---------------------------------------------------------------------------
# The standardized diagnosis output
# ---------------------------------------------------------------------------
class StandardizedDiagnosis(BaseModel):
    """The single canonical diagnosis object produced by the orchestrator."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    timeframe: str
    exchange: str = "synthetic"

    market_state: DiagnosisLabel = DiagnosisLabel.UNDETERMINED
    severity: SeverityLevel = SeverityLevel.HEALTHY_STRUCTURE

    regime: RegimeLabel = RegimeLabel.COMPRESSION
    expectation: ExpectationProfile
    actual: ActualBehaviorProfile

    pathology_scores: PathologyScores = Field(default_factory=PathologyScores)
    contradiction_scores: ContradictionScores = Field(default_factory=ContradictionScores)

    volatility_state: VolatilityState = Field(default_factory=VolatilityState)
    liquidity_state: LiquidityState = Field(default_factory=LiquidityState)
    continuation_state: ContinuationState = Field(default_factory=ContinuationState)
    instability_state: InstabilityState = Field(default_factory=InstabilityState)

    confidence_scores: ConfidenceScores = Field(default_factory=ConfidenceScores)
    escalation_risk: EscalationRisk = Field(default_factory=EscalationRisk)
    structural_health: StructuralHealth = Field(default_factory=StructuralHealth)
    transition_state: StateTransition = Field(default_factory=StateTransition)

    causal_reasoning: List[str] = Field(default_factory=list)
    gpt_interpretation: Optional[str] = None
    diagnostic_summary: str = ""
    extra: Dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def overall_pathology(self) -> float:
        return float(self.pathology_scores.aggregate())

    def is_critical(self) -> bool:
        return self.severity.level >= SeverityLevel.HIGH_RISK_TRANSITION.level

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
