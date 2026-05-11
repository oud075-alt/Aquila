"""Regime archive — long-lived rolling archive of episode records, with
optional regime-tag indexing for fast bucketed retrieval.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from aquila.memory.interfaces import MemoryStore
from aquila.memory.schemas import EpisodeRecord


class RegimeArchive:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store
        self._by_regime: dict[str, list[str]] = defaultdict(list)

    def append(self, record: EpisodeRecord) -> None:
        self._store.append(record)
        self._by_regime[record.regime_tag].append(record.episode_id)

    def all(self) -> Iterable[EpisodeRecord]:
        return self._store.all()

    def by_regime(self, regime: str) -> list[str]:
        return list(self._by_regime.get(regime, []))

    def size(self) -> int:
        return self._store.size()
