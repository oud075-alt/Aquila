from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from aquila.core.types import Symbol
from aquila.ingestion.schemas import OHLCV, RawEvent, RawEventKind
from aquila.replay.runner import ReplayRunner
from aquila.replay.schemas import ReplayContext

router = APIRouter(prefix="/replay", tags=["replay"])


class ReplayBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class ReplayRequest(BaseModel):
    run_id: str
    symbol: Symbol
    bars: list[ReplayBar]


@router.post("/run")
def run(req: ReplayRequest) -> dict:
    events = [
        RawEvent(
            kind=RawEventKind.OHLCV, symbol=req.symbol,
            timestamp=b.timestamp, received_at=b.timestamp, origin="replay",
            ohlcv=OHLCV(timeframe="M1", open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume),
        )
        for b in req.bars
    ]
    ctx = ReplayContext(run_id=req.run_id, symbol=req.symbol)
    result = ReplayRunner(ctx).run(events)
    return {
        "run_id": result.run_id, "ticks": result.ticks,
        "last_layer_confidences": {ln.value: out.confidence for ln, out in result.last_outputs.items()},
    }
