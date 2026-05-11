"""SQLite-backed diagnosis store.

Append-only writes for diagnoses, regime transitions, and contradiction
findings. WAL mode enabled for concurrent reads during writes. Each row
records `schema_version` to support backward-compatible deserialization
(Appendix J).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable, Iterator
from pathlib import Path

from core.persistence.migrations import CURRENT_PERSISTENCE_VERSION, PersistenceMigrator
from core.schemas.diagnosis_envelope import DiagnosisEnvelope


def _ts_ns(envelope: DiagnosisEnvelope) -> int:
    return int(envelope.timestamp.timestamp() * 1_000_000_000)


class SQLiteDiagnosisStore:
    """Thread-safe append-only diagnosis store."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._lock = threading.Lock()
        PersistenceMigrator(self._conn).migrate_to_current()

    @property
    def persistence_version(self) -> int:
        return CURRENT_PERSISTENCE_VERSION

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> SQLiteDiagnosisStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def write_diagnosis(self, envelope: DiagnosisEnvelope) -> int:
        ts_ns = _ts_ns(envelope)
        envelope_json = envelope.model_dump_json()
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO diagnoses (
                    schema_version, symbol, timeframe, source, timestamp_ns,
                    market_state_hash, regime, structural_state,
                    structural_health, escalation_risk, instability_score,
                    pathology_aggregate, contradiction_score, global_confidence,
                    risk_band, defensive_state, validation_failed, envelope_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    envelope.schema_version,
                    envelope.symbol,
                    envelope.timeframe.value,
                    envelope.source.value,
                    ts_ns,
                    envelope.market_state_hash,
                    envelope.regime.regime.value,
                    envelope.pathology.structural_state.value,
                    envelope.structural_health,
                    envelope.escalation_risk,
                    envelope.pathology.instability_score,
                    envelope.pathology.scores.aggregate,
                    envelope.contradiction.contradiction_score,
                    envelope.confidence_state.global_confidence,
                    envelope.risk.risk_band.value,
                    1 if envelope.defensive_state else 0,
                    1 if envelope.validation_failed else 0,
                    envelope_json,
                ),
            )
            row_id = cur.lastrowid

            for finding in envelope.contradiction.findings:
                self._conn.execute(
                    """
                    INSERT INTO contradiction_findings
                        (symbol, timeframe, timestamp_ns, pair_id, policy, severity)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        envelope.symbol,
                        envelope.timeframe.value,
                        ts_ns,
                        finding.pair_id,
                        finding.policy.value,
                        finding.severity,
                    ),
                )

            if envelope.regime.previous_regime is not None and envelope.regime.previous_regime != envelope.regime.regime:
                self._conn.execute(
                    """
                    INSERT INTO regime_transitions
                        (symbol, timeframe, from_regime, to_regime, timestamp_ns,
                         persistence_bars, transition_pressure)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        envelope.symbol,
                        envelope.timeframe.value,
                        envelope.regime.previous_regime.value,
                        envelope.regime.regime.value,
                        ts_ns,
                        envelope.regime.regime_persistence_bars,
                        envelope.regime.transition_pressure,
                    ),
                )

        return int(row_id or 0)

    def write_many(self, envelopes: Iterable[DiagnosisEnvelope]) -> int:
        count = 0
        for env in envelopes:
            self.write_diagnosis(env)
            count += 1
        return count

    def latest(self, *, symbol: str, timeframe: str) -> DiagnosisEnvelope | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT envelope_json FROM diagnoses
                WHERE symbol=? AND timeframe=?
                ORDER BY timestamp_ns DESC LIMIT 1
                """,
                (symbol.upper(), timeframe),
            ).fetchone()
        if row is None:
            return None
        return DiagnosisEnvelope.model_validate_json(row[0])

    def iter_recent(
        self, *, symbol: str, timeframe: str, limit: int = 100
    ) -> Iterator[DiagnosisEnvelope]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT envelope_json FROM diagnoses
                WHERE symbol=? AND timeframe=?
                ORDER BY timestamp_ns DESC LIMIT ?
                """,
                (symbol.upper(), timeframe, int(limit)),
            ).fetchall()
        for r in rows:
            yield DiagnosisEnvelope.model_validate_json(r[0])

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM diagnoses").fetchone()[0])

    def regime_transition_count(self) -> int:
        with self._lock:
            return int(
                self._conn.execute("SELECT COUNT(*) FROM regime_transitions").fetchone()[0]
            )

    def load_envelopes_as_dicts(self) -> list[dict[str, object]]:
        """Return all stored envelopes as plain dicts (utility for tests)."""
        with self._lock:
            rows = self._conn.execute("SELECT envelope_json FROM diagnoses ORDER BY id").fetchall()
        return [json.loads(r[0]) for r in rows]
