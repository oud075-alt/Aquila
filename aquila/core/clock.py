"""Canonical clock authority. Closes audit gap #44.

`Clock` is the single source of "now" for the entire system. Replay uses
`ReplayClock`; live cognition uses `WallClock`. Layers receive a clock via
`LayerContext` — they NEVER call `datetime.now()` directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:  # pragma: no cover - interface
        raise NotImplementedError


class WallClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ReplayClock(Clock):
    """Frozen-time clock used during replay. Deterministic: returns whatever
    timestamp is set, never the real wall clock.
    """

    def __init__(self, t0: datetime):
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
        self._t = t0

    def now(self) -> datetime:
        return self._t

    def advance(self, to: datetime) -> None:
        if to.tzinfo is None:
            to = to.replace(tzinfo=timezone.utc)
        if to < self._t:
            raise ValueError("ReplayClock cannot move backwards")
        self._t = to
