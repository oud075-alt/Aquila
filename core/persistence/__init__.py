"""Phase 0F — Persistence substrate.

SQLite for metadata (diagnoses, regime transitions, contradictions, memory).
Parquet for time-series (pathology scores, confidence) — append-only,
schema-versioned, deterministically serialized.
"""

from core.persistence.memory_store import MemoryEntry, MemoryStore
from core.persistence.migrations import (
    CURRENT_PERSISTENCE_VERSION,
    PersistenceMigrator,
)
from core.persistence.sqlite_store import SQLiteDiagnosisStore
from core.persistence.timeseries_store import TimeSeriesStore

__all__ = [
    "CURRENT_PERSISTENCE_VERSION",
    "MemoryEntry",
    "MemoryStore",
    "PersistenceMigrator",
    "SQLiteDiagnosisStore",
    "TimeSeriesStore",
]
