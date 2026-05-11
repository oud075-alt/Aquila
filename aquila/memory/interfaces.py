from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from aquila.memory.schemas import EpisodeRecord, MemoryQuery, MemoryResult


class MemoryStore(ABC):
    @abstractmethod
    def append(self, record: EpisodeRecord) -> None:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def all(self) -> Iterable[EpisodeRecord]:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def size(self) -> int:  # pragma: no cover
        raise NotImplementedError


class SimilarityIndex(ABC):
    @abstractmethod
    def search(self, query: MemoryQuery, records: Iterable[EpisodeRecord]) -> list[MemoryResult]:
        raise NotImplementedError
