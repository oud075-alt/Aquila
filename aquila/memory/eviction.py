"""Memory eviction policy — closes audit gap #49.

Default: capacity-bounded FIFO (handled by `InMemoryStore`'s deque).
This module provides a time-window policy for stores that don't auto-evict.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aquila.memory.schemas import EpisodeRecord


class TimeWindowEvictionPolicy:
    def __init__(self, max_age_days: int = 365):
        self.max_age = timedelta(days=max_age_days)

    def keep(self, record: EpisodeRecord, now: datetime | None = None) -> bool:
        n = now or datetime.now(timezone.utc)
        return (n - record.timestamp) <= self.max_age
