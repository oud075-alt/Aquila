from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Symbol


class ReplayContext(BaseModel):
    """Frozen execution context for a replay run."""

    model_config = ConfigDict(frozen=True)
    run_id: str
    symbol: Symbol
    seed: int = 0
    write_memory: bool = False
    origin: Literal["replay", "synthetic"] = "replay"
    notes: list[str] = Field(default_factory=list)


class ReplaySlice(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: datetime
    end: datetime
