"""Runtime wiring for the FastAPI app — singleton state container."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from core.ingestion.base_adapter import IngestionEvent
from core.ingestion.replay_adapter import ReplayAdapter
from core.observability import HealthMonitor, default_registry, get_logger, init_logging
from core.orchestrator import DiagnosisCoordinator
from core.persistence import MemoryStore, SQLiteDiagnosisStore, TimeSeriesStore
from core.schemas.diagnosis_envelope import DiagnosisEnvelope
from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL

DEFAULT_DATA_ROOT: Path = Path(
    os.environ.get("MSPIS_DATA_ROOT", str(Path.cwd() / "mspis-data"))
)


class Runtime:
    """Singleton runtime wiring diagnosis coordinator + persistence + health."""

    _instance: "Runtime | None" = None

    def __init__(self, *, data_root: Path | None = None) -> None:
        init_logging(level=os.environ.get("MSPIS_LOG_LEVEL", "INFO"))
        self.log = get_logger("api.runtime")
        self.data_root = Path(data_root or DEFAULT_DATA_ROOT)
        self.data_root.mkdir(parents=True, exist_ok=True)

        self.coordinator = DiagnosisCoordinator(
            symbol=DEFAULT_SYMBOL,
            source=SourceMode.REPLAY,
            timeframes=(Timeframe.ONE_MIN,),
        )
        self.sqlite = SQLiteDiagnosisStore(self.data_root / "mspis.db")
        self.timeseries = TimeSeriesStore(self.data_root / "timeseries")
        self.memory = MemoryStore(self.data_root / "memory.db")
        self.health = HealthMonitor()
        self.metrics = default_registry
        self._lock = asyncio.Lock()
        self._latest: DiagnosisEnvelope | None = None
        self._started_at = datetime.now(tz=timezone.utc)

    @classmethod
    def instance(cls) -> "Runtime":
        if cls._instance is None:
            cls._instance = Runtime()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    async def ingest_event(self, event: IngestionEvent) -> DiagnosisEnvelope:
        async with self._lock:
            envelope = await self.coordinator.diagnose_event(event)
            self.sqlite.write_diagnosis(envelope)
            self.timeseries.append(envelope)
            self._latest = envelope
            self.health.record_diagnosis(
                latency_ms=0.0,
                confidence=envelope.confidence_state.global_confidence,
            )
            if event.bar.is_partial:
                self.health.record_stale_warning()
            return envelope

    async def run_replay(self, parquet_path: str | Path) -> int:
        adapter = ReplayAdapter(parquet_path, timeframe=Timeframe.ONE_MIN)
        n = 0
        async for event in adapter.stream():
            await self.ingest_event(event)
            n += 1
        self.timeseries.flush()
        self.log.info("replay_complete", n=n, parquet=str(parquet_path))
        return n

    def latest(self) -> DiagnosisEnvelope | None:
        if self._latest is not None:
            return self._latest
        return self.sqlite.latest(symbol=DEFAULT_SYMBOL, timeframe=Timeframe.ONE_MIN.value)

    @property
    def started_at(self) -> datetime:
        return self._started_at
