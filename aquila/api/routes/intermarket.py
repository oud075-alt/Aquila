from __future__ import annotations

from fastapi import APIRouter, Depends

from aquila.api.deps import AppState, state

router = APIRouter(prefix="/intermarket", tags=["intermarket"])


@router.get("/report")
def report(s: AppState = Depends(state)) -> dict:
    return s.intermarket.report().model_dump()
