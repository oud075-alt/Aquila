"""Closed enumerations referenced by every MSPIS module.

These enums are CONTRACTUAL. Inventing new members at runtime is forbidden
(Appendix B). Adding members requires a schema_version bump and an ADR.
"""

from __future__ import annotations

from enum import StrEnum


class Timeframe(StrEnum):
    """Mandatory multi-timeframe alphabet (Appendix C)."""

    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    ONE_HOUR = "1h"
    FOUR_HOUR = "4h"

    @property
    def seconds(self) -> int:
        return _TIMEFRAME_SECONDS[self]

    @property
    def order(self) -> int:
        return _TIMEFRAME_ORDER[self]


_TIMEFRAME_SECONDS: dict[Timeframe, int] = {
    Timeframe.ONE_MIN: 60,
    Timeframe.FIVE_MIN: 300,
    Timeframe.FIFTEEN_MIN: 900,
    Timeframe.ONE_HOUR: 3600,
    Timeframe.FOUR_HOUR: 14400,
}

_TIMEFRAME_ORDER: dict[Timeframe, int] = {
    Timeframe.ONE_MIN: 0,
    Timeframe.FIVE_MIN: 1,
    Timeframe.FIFTEEN_MIN: 2,
    Timeframe.ONE_HOUR: 3,
    Timeframe.FOUR_HOUR: 4,
}


class SourceMode(StrEnum):
    """Where the market data originated. Replay is the deterministic default."""

    REPLAY = "replay"
    LIVE_WS = "live_ws"
    LIVE_REST = "live_rest"


class Regime(StrEnum):
    """Closed regime taxonomy (Appendix B). No new members at runtime."""

    TREND_HEALTHY = "TREND_HEALTHY"
    TREND_FRAGILE = "TREND_FRAGILE"
    COMPRESSION_HEALTHY = "COMPRESSION_HEALTHY"
    COMPRESSION_UNSTABLE = "COMPRESSION_UNSTABLE"
    EXPANSION_HEALTHY = "EXPANSION_HEALTHY"
    EXPANSION_UNSTABLE = "EXPANSION_UNSTABLE"
    MEAN_REVERSION = "MEAN_REVERSION"
    LIQUIDITY_VACUUM = "LIQUIDITY_VACUUM"
    DEFENSIVE = "DEFENSIVE"
    ENTROPIC = "ENTROPIC"
    TRANSITIONAL = "TRANSITIONAL"


class StructuralState(StrEnum):
    """Per-bar structural state alphabet (Appendix U)."""

    UP_CONTINUATION = "UP_CONTINUATION"
    DOWN_CONTINUATION = "DOWN_CONTINUATION"
    COMPRESSION = "COMPRESSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    LIQUIDITY_STALL = "LIQUIDITY_STALL"
    REVERSAL_PRESSURE = "REVERSAL_PRESSURE"
    CHAOTIC_TRANSITION = "CHAOTIC_TRANSITION"


class ContradictionPolicy(StrEnum):
    """Contradiction handling policies (Appendix N + X)."""

    INVALID = "INVALID"
    UNSTABLE = "UNSTABLE"
    CRITICAL = "CRITICAL"


class RiskBand(StrEnum):
    """Coarse risk bands. Numeric risk lives in scores; this is the readable label."""

    HEALTHY = "HEALTHY"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StrategyEnvironment(StrEnum):
    """Structural environment categories produced by the strategy router (Phase 3)."""

    TREND_CONTINUATION = "TREND_CONTINUATION"
    MEAN_REVERSION = "MEAN_REVERSION"
    COMPRESSION = "COMPRESSION"
    DEFENSIVE = "DEFENSIVE"
    UNSTABLE = "UNSTABLE"
    HIGH_ENTROPY = "HIGH_ENTROPY"
