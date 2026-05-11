from __future__ import annotations

from fastapi import APIRouter, Depends

from aquila.api.deps import AppState, state

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/run")
def run(s: AppState = Depends(state)) -> dict:
    suite = s.make_validation_suite()
    return suite.run().model_dump()
