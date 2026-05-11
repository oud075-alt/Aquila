"""Similarity search — cosine over fingerprint vectors."""

from __future__ import annotations

import math
from typing import Iterable

from aquila.memory.interfaces import SimilarityIndex
from aquila.memory.schemas import EpisodeRecord, MemoryQuery, MemoryResult


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SimpleSimilarityIndex(SimilarityIndex):
    def search(self, query: MemoryQuery, records: Iterable[EpisodeRecord]) -> list[MemoryResult]:
        scored: list[MemoryResult] = []
        for rec in records:
            if query.symbol is not None and rec.symbol != query.symbol:
                continue
            sim = _cosine(query.fingerprint.vector, rec.fingerprint.vector)
            if sim < query.min_similarity:
                continue
            scored.append(MemoryResult(record=rec, similarity=sim))
        scored.sort(key=lambda r: r.similarity, reverse=True)
        return scored[: query.top_k]
