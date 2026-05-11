from __future__ import annotations

from fastapi import APIRouter, Depends

from aquila.api.deps import AppState, state

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict:
    return {"status": "alive"}


@router.get("/ready")
def readiness(s: AppState = Depends(state)) -> dict:
    return {
        "status": "ready",
        "audit_chain_ok": s.orchestrator.audit.verify(),
        "events_stored": len(s.event_store),
    }
