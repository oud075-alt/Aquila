"""Phase 5 episodic memory store.

Stores structured memory entries with arbitrary JSON payload and an
optional realized outcome score (populated later when ground truth
becomes available — Appendix E).

The MemoryStore is shared by:
    - Phase 5 adaptive_learning.py (writes)
    - Phase 1-4 (reads) when adaptive recalibration kicks in
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.persistence.migrations import PersistenceMigrator
from core.schemas.enums import Timeframe


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    id: int
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    kind: str
    payload: dict[str, object]
    outcome_score: float | None


class MemoryStore:
    """Episodic learning memory backed by SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._lock = threading.Lock()
        PersistenceMigrator(self._conn).migrate_to_current()

    def remember(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        timestamp: datetime,
        kind: str,
        payload: dict[str, object],
        outcome_score: float | None = None,
    ) -> int:
        ts_ns = int(timestamp.timestamp() * 1_000_000_000)
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO learning_memory
                    (symbol, timeframe, timestamp_ns, kind, payload_json, outcome_score)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    symbol.upper(),
                    timeframe.value,
                    ts_ns,
                    kind,
                    json.dumps(payload, sort_keys=True),
                    outcome_score,
                ),
            )
        return int(cur.lastrowid or 0)

    def assign_outcome(self, entry_id: int, *, outcome_score: float) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE learning_memory SET outcome_score=? WHERE id=?",
                (float(outcome_score), int(entry_id)),
            )

    def recall(self, *, kind: str | None = None, limit: int = 256) -> list[MemoryEntry]:
        with self._lock:
            if kind is None:
                rows = self._conn.execute(
                    "SELECT id, symbol, timeframe, timestamp_ns, kind, payload_json, outcome_score "
                    "FROM learning_memory ORDER BY id DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, symbol, timeframe, timestamp_ns, kind, payload_json, outcome_score "
                    "FROM learning_memory WHERE kind=? ORDER BY id DESC LIMIT ?",
                    (kind, int(limit)),
                ).fetchall()
        out: list[MemoryEntry] = []
        for r in rows:
            out.append(
                MemoryEntry(
                    id=int(r[0]),
                    symbol=str(r[1]),
                    timeframe=Timeframe(r[2]),
                    timestamp=datetime.fromtimestamp(int(r[3]) / 1e9, tz=timezone.utc),
                    kind=str(r[4]),
                    payload=json.loads(r[5]),
                    outcome_score=None if r[6] is None else float(r[6]),
                )
            )
        return out

    def iter_pending(self) -> Iterator[MemoryEntry]:
        """Iterate entries that still lack an outcome_score."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, symbol, timeframe, timestamp_ns, kind, payload_json, outcome_score "
                "FROM learning_memory WHERE outcome_score IS NULL ORDER BY id ASC"
            ).fetchall()
        for r in rows:
            yield MemoryEntry(
                id=int(r[0]),
                symbol=str(r[1]),
                timeframe=Timeframe(r[2]),
                timestamp=datetime.fromtimestamp(int(r[3]) / 1e9, tz=timezone.utc),
                kind=str(r[4]),
                payload=json.loads(r[5]),
                outcome_score=None,
            )

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM learning_memory").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()
