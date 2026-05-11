"""Timeframe abstraction shared by ingestion, structural, temporal layers.

Closes prompt audit gap #11 (no timeframe/bar-close semantics).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

    @property
    def minutes(self) -> int:
        return {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440,
        }[self]

    @property
    def seconds(self) -> int:
        return self.minutes * 60

    def floor(self, ts: datetime) -> datetime:
        """Return the bar-open timestamp containing `ts`."""
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        epoch = int(ts.timestamp())
        floored = epoch - (epoch % self.seconds)
        return datetime.fromtimestamp(floored, tz=timezone.utc)

    def next_close(self, ts: datetime) -> datetime:
        """Return the bar-close timestamp after `ts`."""
        return self.floor(ts) + timedelta(seconds=self.seconds)


ALL_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe.M1,
    Timeframe.M5,
    Timeframe.M15,
    Timeframe.H1,
    Timeframe.H4,
    Timeframe.D1,
)


class TimeframeSet:
    """Immutable ordered set of timeframes with hierarchy ordering."""

    def __init__(self, tfs: Iterable[Timeframe]):
        self._tfs: tuple[Timeframe, ...] = tuple(sorted(set(tfs), key=lambda t: t.minutes))

    def __iter__(self):
        return iter(self._tfs)

    def __contains__(self, tf: Timeframe) -> bool:
        return tf in self._tfs

    def __len__(self) -> int:
        return len(self._tfs)

    @property
    def lowest(self) -> Timeframe:
        return self._tfs[0]

    @property
    def highest(self) -> Timeframe:
        return self._tfs[-1]

    def above(self, tf: Timeframe) -> tuple[Timeframe, ...]:
        return tuple(x for x in self._tfs if x.minutes > tf.minutes)

    def below(self, tf: Timeframe) -> tuple[Timeframe, ...]:
        return tuple(x for x in self._tfs if x.minutes < tf.minutes)
