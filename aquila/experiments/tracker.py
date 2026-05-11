from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import utcnow


class Experiment(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    hypothesis: str
    started_at: datetime = Field(default_factory=utcnow)
    parameters: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)


class ExperimentTracker:
    def __init__(self) -> None:
        self._experiments: list[Experiment] = []

    def register(self, e: Experiment) -> Experiment:
        self._experiments.append(e)
        return e

    def all(self) -> list[Experiment]:
        return list(self._experiments)
