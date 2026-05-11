from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import utcnow


class OntologyEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    namespace: str
    name: str
    description: str
    version: str = "1.0.0"


class OntologySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    captured_at: datetime = Field(default_factory=utcnow)
    entries: list[OntologyEntry] = Field(default_factory=list)
    version: str = "1.0.0"
