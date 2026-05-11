from __future__ import annotations

from fastapi import APIRouter, Depends

from aquila.api.deps import AppState, state

router = APIRouter(prefix="/narrative", tags=["narrative"])


@router.get("/{correlation_id}")
def narrative(correlation_id: str, s: AppState = Depends(state)) -> dict:
    outs = s.latest_by_corr.get(correlation_id, {})
    if not outs:
        return {"error": "not_found"}
    return s.narrative.explain(outs).model_dump()
