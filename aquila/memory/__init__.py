"""Layer 4 — Episodic Market Memory.

Sub-modules:
- schemas.py             : EpisodeFingerprint, EpisodeRecord, MemoryQuery, MemoryResult
- interfaces.py          : MemoryStore, FingerprintExtractor, SimilarityIndex
- fingerprint.py         : structural-state fingerprint extractor
- store.py               : InMemoryStore, JsonlStore
- index.py               : SimpleSimilarityIndex (cosine on fingerprint vector)
- archive.py             : RegimeArchive (rolling, append-only)
- recall.py              : structural-sequence recall
- eviction.py            : retention/eviction policy
- engine.py              : EpisodicMemoryLayer (orchestrates the above)
- replay_integration.py  : replay-mode hooks (no real-time writes)
"""

from aquila.memory.engine import EpisodicMemoryLayer
from aquila.memory.fingerprint import FingerprintExtractor
from aquila.memory.index import SimpleSimilarityIndex
from aquila.memory.schemas import (
    EpisodeFingerprint,
    EpisodeRecord,
    MemoryQuery,
    MemoryRecall,
    MemoryResult,
)
from aquila.memory.store import InMemoryStore, JsonlStore

__all__ = [
    "EpisodicMemoryLayer",
    "FingerprintExtractor",
    "SimpleSimilarityIndex",
    "EpisodeFingerprint",
    "EpisodeRecord",
    "MemoryQuery",
    "MemoryRecall",
    "MemoryResult",
    "InMemoryStore",
    "JsonlStore",
]
