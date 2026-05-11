from __future__ import annotations

from fastapi import APIRouter, Depends

from aquila.api.deps import AppState, state

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/size")
def size(s: AppState = Depends(state)) -> dict:
    return {"archive_size": s.orchestrator.memory.archive.size()}
