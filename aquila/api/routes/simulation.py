from __future__ import annotations

from fastapi import APIRouter

from aquila.core.types import Symbol
from aquila.simulation.engine import SimulationEngine

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/stress/{symbol}")
def stress(symbol: Symbol, cycles: int = 50, vol_mult: float = 3.0) -> dict:
    return SimulationEngine().stress(symbol, n_cycles=cycles, volatility_multiplier=vol_mult).model_dump()
