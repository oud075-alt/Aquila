"""Schema migration registry for persistence layers (Appendix J).

Phase 0 ships at version 1. Future schema changes add migrations here; the
SQLiteDiagnosisStore and TimeSeriesStore consult this registry on open.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

CURRENT_PERSISTENCE_VERSION: int = 1


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    description: str
    apply: Callable[[sqlite3.Connection], None]


def _v1_initial(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS persistence_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schema_version TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            source TEXT NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            market_state_hash TEXT NOT NULL,
            regime TEXT NOT NULL,
            structural_state TEXT NOT NULL,
            structural_health REAL NOT NULL,
            escalation_risk REAL NOT NULL,
            instability_score REAL NOT NULL,
            pathology_aggregate REAL NOT NULL,
            contradiction_score REAL NOT NULL,
            global_confidence REAL NOT NULL,
            risk_band TEXT NOT NULL,
            defensive_state INTEGER NOT NULL,
            validation_failed INTEGER NOT NULL,
            envelope_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_diagnoses_symbol_ts ON diagnoses(symbol, timestamp_ns);
        CREATE INDEX IF NOT EXISTS idx_diagnoses_regime ON diagnoses(regime);

        CREATE TABLE IF NOT EXISTS regime_transitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            from_regime TEXT,
            to_regime TEXT NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            persistence_bars INTEGER NOT NULL,
            transition_pressure REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contradiction_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            pair_id TEXT NOT NULL,
            policy TEXT NOT NULL,
            severity REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_contradiction_pair ON contradiction_findings(pair_id);

        CREATE TABLE IF NOT EXISTS learning_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            outcome_score REAL
        );
        CREATE INDEX IF NOT EXISTS idx_learning_kind ON learning_memory(kind);
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO persistence_meta(key, value) VALUES (?, ?)",
        ("version", str(CURRENT_PERSISTENCE_VERSION)),
    )
    conn.commit()


_MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, description="initial schema", apply=_v1_initial),
)


class PersistenceMigrator:
    """Apply outstanding migrations and validate schema version."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def current_version(self) -> int:
        cur = self.conn.execute(
            "SELECT value FROM persistence_meta WHERE key='version'"
        ).fetchone() if self._meta_table_exists() else None
        return int(cur[0]) if cur else 0

    def _meta_table_exists(self) -> bool:
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='persistence_meta'"
        ).fetchone()
        return row is not None

    def migrate_to_current(self) -> int:
        current = self.current_version()
        applied = 0
        for migration in _MIGRATIONS:
            if migration.version > current:
                migration.apply(self.conn)
                applied += 1
        if applied:
            self.conn.execute(
                "INSERT OR REPLACE INTO persistence_meta(key, value) VALUES (?, ?)",
                ("version", str(CURRENT_PERSISTENCE_VERSION)),
            )
            self.conn.commit()
        return applied
