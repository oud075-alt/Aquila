from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aquila.api.deps import AppState, state
from aquila.core.types import Symbol
from aquila.primitives import PrimitiveBar

router = APIRouter(prefix="/cognition", tags=["cognition"])


class TickRequest(BaseModel):
    symbol: Symbol
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class TickResponse(BaseModel):
    correlation_id: str
    layers: dict


@router.post("/tick", response_model=TickResponse)
def tick(req: TickRequest, s: AppState = Depends(state)) -> TickResponse:
    bar = PrimitiveBar(
        timestamp=req.timestamp, open=req.open, high=req.high,
        low=req.low, close=req.close, volume=req.volume,
    )
    outs = s.orchestrator.run_tick(req.symbol, bar)
    s.record(outs)
    return TickResponse(
        correlation_id=next(iter(outs.values())).correlation_id,
        layers={ln.value: {
            "event_id": o.event_id,
            "confidence": o.confidence,
            "visibility": o.visibility,
            "payload": o.payload.model_dump() if hasattr(o.payload, "model_dump") else {},
        } for ln, o in outs.items()},
    )


@router.get("/lifecycle/{correlation_id}")
def lifecycle(correlation_id: str, s: AppState = Depends(state)) -> dict:
    outs = s.latest_by_corr.get(correlation_id, {})
    if not outs:
        return {"error": "not_found"}
    return s.orchestrator.lifecycle(outs).model_dump()
