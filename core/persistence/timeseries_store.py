"""Append-only Parquet time-series store for pathology + confidence history.

The store maintains an in-memory buffer and flushes to a partitioned
Parquet dataset on `.flush()`. Deterministic serialization: rows are
written in arrival order, columns in a fixed order, and PyArrow's
default compression is used (snappy) which is deterministic.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from core.schemas.diagnosis_envelope import DiagnosisEnvelope

SCHEMA_VERSION: str = "0.1.0"

_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "timestamp_ns",
    "symbol",
    "timeframe",
    "source",
    "regime",
    "structural_state",
    "entropy_instability",
    "autocorrelation_breakdown",
    "liquidity_imbalance",
    "dispersion_shock",
    "volatility_disorder",
    "continuation_decay",
    "pathology_aggregate",
    "structural_health",
    "instability_score",
    "escalation_risk",
    "contradiction_score",
    "global_confidence",
    "raw_geometric_mean",
    "instability_penalty",
    "contradiction_penalty",
    "entropy_penalty",
    "validation_failed",
    "defensive_state",
)


def _envelope_to_row(envelope: DiagnosisEnvelope) -> dict[str, object]:
    p = envelope.pathology.scores
    c = envelope.confidence_state
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp_ns": int(envelope.timestamp.timestamp() * 1_000_000_000),
        "symbol": envelope.symbol,
        "timeframe": envelope.timeframe.value,
        "source": envelope.source.value,
        "regime": envelope.regime.regime.value,
        "structural_state": envelope.pathology.structural_state.value,
        "entropy_instability": p.entropy_instability,
        "autocorrelation_breakdown": p.autocorrelation_breakdown,
        "liquidity_imbalance": p.liquidity_imbalance,
        "dispersion_shock": p.dispersion_shock,
        "volatility_disorder": p.volatility_disorder,
        "continuation_decay": p.continuation_decay,
        "pathology_aggregate": p.aggregate,
        "structural_health": envelope.structural_health,
        "instability_score": envelope.pathology.instability_score,
        "escalation_risk": envelope.escalation_risk,
        "contradiction_score": envelope.contradiction.contradiction_score,
        "global_confidence": c.global_confidence,
        "raw_geometric_mean": c.raw_geometric_mean,
        "instability_penalty": c.instability_penalty,
        "contradiction_penalty": c.contradiction_penalty,
        "entropy_penalty": c.entropy_penalty,
        "validation_failed": envelope.validation_failed,
        "defensive_state": envelope.defensive_state,
    }


class TimeSeriesStore:
    """Append-only Parquet writer with deterministic ordering."""

    def __init__(self, parquet_dir: str | Path, *, batch_size: int = 1024) -> None:
        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self._buffer: list[dict[str, object]] = []
        self._lock = threading.Lock()
        self._part_counter = 0

    def append(self, envelope: DiagnosisEnvelope) -> None:
        row = _envelope_to_row(envelope)
        with self._lock:
            self._buffer.append(row)
            if len(self._buffer) >= self.batch_size:
                self._flush_locked()

    def append_many(self, envelopes: Iterable[DiagnosisEnvelope]) -> int:
        n = 0
        for env in envelopes:
            self.append(env)
            n += 1
        return n

    def flush(self) -> Path | None:
        with self._lock:
            return self._flush_locked()

    def _flush_locked(self) -> Path | None:
        if not self._buffer:
            return None
        df = pd.DataFrame(self._buffer, columns=list(_COLUMNS))
        table = pa.Table.from_pandas(df, preserve_index=False)
        part = self.parquet_dir / f"part-{self._part_counter:08d}.parquet"
        pq.write_table(table, part, compression="snappy")
        self._part_counter += 1
        self._buffer.clear()
        return part

    def read_all(self) -> pd.DataFrame:
        files = sorted(self.parquet_dir.glob("part-*.parquet"))
        if not files:
            return pd.DataFrame(columns=list(_COLUMNS))
        frames = [pq.read_table(f).to_pandas() for f in files]
        return pd.concat(frames, ignore_index=True)
