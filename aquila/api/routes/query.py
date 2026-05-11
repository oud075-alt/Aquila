from __future__ import annotations

from fastapi import APIRouter, Depends

from aquila.api.deps import AppState, state
from aquila.core.types import Symbol
from aquila.query.schemas import (
    CausalTraceQuery,
    PathologyHistoryQuery,
    StructuralStateQuery,
)

router = APIRouter(prefix="/query", tags=["query"])


@router.get("/structural/{symbol}")
def structural(symbol: Symbol, last_n: int = 50, s: AppState = Depends(state)) -> dict:
    eng = s.make_query_engine()
    return eng.structural_states(StructuralStateQuery(symbol=symbol, last_n=last_n)).model_dump()


@router.get("/pathology/{symbol}")
def pathology(symbol: Symbol, last_n: int = 50, s: AppState = Depends(state)) -> dict:
    eng = s.make_query_engine()
    return eng.pathology_history(PathologyHistoryQuery(symbol=symbol, last_n=last_n)).model_dump()


@router.get("/causal/{correlation_id}")
def causal(correlation_id: str, s: AppState = Depends(state)) -> dict:
    eng = s.make_query_engine()
    return eng.causal_trace(CausalTraceQuery(correlation_id=correlation_id)).model_dump()
