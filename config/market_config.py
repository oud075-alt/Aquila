"""Market-specific configuration: instruments, timeframes, regime thresholds.

The objects defined here are pure-Python data classes (not env-backed) so
that they can be overridden programmatically from research notebooks or
tests without polluting the environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List


@dataclass(frozen=True)
class TimeframeSpec:
    """Mapping between human timeframe codes and seconds.

    Used by the sensory layer to schedule polling intervals and by the
    expectation layer to convert lookback windows into bar counts.
    """

    code: str
    seconds: int


TIMEFRAMES: Dict[str, TimeframeSpec] = {
    "1s": TimeframeSpec("1s", 1),
    "5s": TimeframeSpec("5s", 5),
    "15s": TimeframeSpec("15s", 15),
    "1m": TimeframeSpec("1m", 60),
    "3m": TimeframeSpec("3m", 180),
    "5m": TimeframeSpec("5m", 300),
    "15m": TimeframeSpec("15m", 900),
    "30m": TimeframeSpec("30m", 1800),
    "1h": TimeframeSpec("1h", 3600),
    "2h": TimeframeSpec("2h", 7200),
    "4h": TimeframeSpec("4h", 14400),
    "6h": TimeframeSpec("6h", 21600),
    "12h": TimeframeSpec("12h", 43200),
    "1d": TimeframeSpec("1d", 86400),
    "1w": TimeframeSpec("1w", 604800),
}


@dataclass
class PathologyThresholds:
    """Severity thresholds used by the disease classifier.

    Each level corresponds to the pathology hierarchy mandated by the
    system specification (LEVEL 0 … LEVEL 5).
    """

    healthy: float = 0.20            # below = HEALTHY_STRUCTURE
    minor: float = 0.35              # MINOR_INSTABILITY
    fragile: float = 0.50            # FRAGILE_STRUCTURE
    high_risk: float = 0.65          # HIGH_RISK_TRANSITION
    pre_collapse: float = 0.80       # PRE_COLLAPSE
    # Anything ≥ pre_collapse and with structural_failure flag → STRUCTURAL_FAILURE


@dataclass
class ContradictionWeights:
    """Weights for the contradiction engine (sum need not equal 1)."""

    momentum_vs_price: float = 1.20
    volume_vs_price: float = 1.10
    volatility_vs_continuation: float = 1.00
    range_vs_acceptance: float = 0.95
    breadth_vs_expansion: float = 0.90
    liquidity_vs_move: float = 1.15
    wick_vs_body: float = 0.85
    entropy_vs_direction: float = 1.05


@dataclass
class MarketConfig:
    """Top-level market configuration container."""

    timeframes: Dict[str, TimeframeSpec] = field(default_factory=lambda: dict(TIMEFRAMES))
    thresholds: PathologyThresholds = field(default_factory=PathologyThresholds)
    contradiction_weights: ContradictionWeights = field(default_factory=ContradictionWeights)

    # Healthy-physiology reference parameters.
    healthy_trend_min_r2: float = 0.55          # rolling regression R² for healthy trend
    healthy_continuation_persistence: float = 0.60  # AR(1) autocorr expected when healthy
    healthy_volatility_expansion_ratio: float = 1.25  # post-breakout ATR vs prior ATR
    healthy_volume_participation: float = 0.85  # vol on breakout / median(volume)

    # Liquidity & stress reference parameters.
    stress_window_bars: int = 50
    liquidity_window_bars: int = 50
    instability_window_bars: int = 100
    compression_lookback: int = 50

    # Anomaly aggregation.
    min_bars_for_diagnosis: int = 120
    confidence_minimum_samples: int = 80

    def timeframe_seconds(self, code: str) -> int:
        if code not in self.timeframes:
            raise KeyError(f"Unknown timeframe: {code}")
        return self.timeframes[code].seconds

    def supported_timeframes(self) -> List[str]:
        return list(self.timeframes.keys())


@lru_cache(maxsize=1)
def get_market_config() -> MarketConfig:
    return MarketConfig()
