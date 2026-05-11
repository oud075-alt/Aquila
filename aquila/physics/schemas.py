from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TransitionVelocity(BaseModel):
    model_config = ConfigDict(frozen=True)
    from_state: str
    to_state: str
    bars_held: int
    rate_per_bar: float


class PhysicsReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    last_transition: TransitionVelocity | None = None
    instability: float = 0.0
    accelerating: bool = False
    collapsing: bool = False
    rationale: list[str] = Field(default_factory=list)
