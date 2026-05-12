"""FastAPI surface for MSPIS (Phase 0H).

All endpoints return the latest available state from the runtime singleton.
Endpoints are async, schema-validated via Pydantic v2, and forbid every
field listed in Appendix I (Behavior Boundary — enforced by Phase 0
CI in tests/test_behavior_boundary.py).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from api.runtime import Runtime
from core.observability import init_logging
from core.schemas import (
    ConfidenceState,
    ContradictionReport,
    DiagnosisEnvelope,
    PathologyReport,
    RegimeState,
    RiskState,
    TimeframeContext,
)

API_VERSION: str = "v0.1"


class APIInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    version: str
    schema_version: str
    purpose: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    healthy: bool
    api_version: str
    uptime_seconds: float
    last_diagnosis_at: datetime | None
    confidence_degradation: float
    stale_warnings: int


class SystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    api_version: str
    started_at: datetime
    diagnoses_recorded: int
    regime_transitions_recorded: int
    last_diagnosis_at: datetime | None
    latest_global_confidence: float | None


def _runtime() -> Runtime:
    return Runtime.instance()


init_logging()
app = FastAPI(
    title="MSPIS — Market Structural Pathology Intelligence System",
    version=API_VERSION,
    description=(
        "Structural market cognition. NOT a trading bot. NOT a signal generator. "
        "See Appendix I for the forbidden output surface enforced by CI."
    ),
)


@app.get("/", response_model=APIInfo)
async def root() -> APIInfo:
    return APIInfo(
        name="MSPIS",
        version=API_VERSION,
        schema_version="0.1.0",
        purpose="structural_market_cognition",
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    rt = _runtime()
    snap = rt.health.snapshot()
    return HealthResponse(
        healthy=snap.healthy,
        api_version=API_VERSION,
        uptime_seconds=snap.uptime_seconds,
        last_diagnosis_at=snap.last_diagnosis_at,
        confidence_degradation=snap.confidence_degradation,
        stale_warnings=snap.stale_warnings,
    )


@app.get("/system/status", response_model=SystemStatus)
async def system_status() -> SystemStatus:
    rt = _runtime()
    latest = rt.latest()
    return SystemStatus(
        api_version=API_VERSION,
        started_at=rt.started_at,
        diagnoses_recorded=rt.sqlite.count(),
        regime_transitions_recorded=rt.sqlite.regime_transition_count(),
        last_diagnosis_at=latest.timestamp if latest else None,
        latest_global_confidence=(
            latest.confidence_state.global_confidence if latest else None
        ),
    )


def _require_latest() -> DiagnosisEnvelope:
    latest = _runtime().latest()
    if latest is None:
        raise HTTPException(
            status_code=404,
            detail="no diagnosis recorded yet — ingest data via POST /system/replay",
        )
    return latest


@app.get("/diagnosis", response_model=DiagnosisEnvelope)
async def diagnosis() -> DiagnosisEnvelope:
    return _require_latest()


@app.get("/pathology", response_model=PathologyReport)
async def pathology() -> PathologyReport:
    return _require_latest().pathology


@app.get("/contradictions", response_model=ContradictionReport)
async def contradictions() -> ContradictionReport:
    return _require_latest().contradiction


@app.get("/risk", response_model=RiskState)
async def risk() -> RiskState:
    return _require_latest().risk


@app.get("/context", response_model=TimeframeContext | None)
async def context() -> TimeframeContext | None:
    return _require_latest().timeframe_context


@app.get("/regime", response_model=RegimeState)
async def regime() -> RegimeState:
    return _require_latest().regime


@app.get("/confidence", response_model=ConfidenceState)
async def confidence() -> ConfidenceState:
    return _require_latest().confidence_state


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    rt = _runtime()
    snap = rt.metrics.snapshot()
    health = rt.health.snapshot()
    return {
        "api_version": API_VERSION,
        "schema_version": "0.1.0",
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "uptime_seconds": health.uptime_seconds,
        "stale_warnings": health.stale_warnings,
        "memory_warnings": health.memory_warnings,
        "confidence_degradation": health.confidence_degradation,
        "counters": snap["counters"],
        "histograms": snap["histograms"],
    }


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parquet_path: str


@app.post("/system/replay")
async def system_replay(req: ReplayRequest) -> JSONResponse:
    rt = _runtime()
    path = Path(req.parquet_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"parquet not found: {path}")
    n = await rt.run_replay(path)
    return JSONResponse(
        {
            "api_version": API_VERSION,
            "events_processed": n,
            "diagnoses_recorded": rt.sqlite.count(),
        }
    )
