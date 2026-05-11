from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import LayerName, Symbol
from aquila.pathology.schemas import PathologyReport
from aquila.structural.schemas import StructuralDiagnosis


class EpisodeFingerprint(BaseModel):
    """Compact, comparable representation of a structural moment.

    `vector` is a low-dimensional float vector that supports cosine
    similarity in `SimpleSimilarityIndex`. `tags` are categorical hooks
    (structural state, pathology kinds, regime tag).
    """

    model_config = ConfigDict(frozen=True)
    vector: list[float]
    tags: list[str] = Field(default_factory=list)
    schema_version: str = "1.0.0"


class EpisodeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Symbol
    timestamp: datetime
    diagnosis: StructuralDiagnosis
    pathology: PathologyReport
    fingerprint: EpisodeFingerprint
    regime_tag: str = "unknown"
    origin: str = "real"
    schema_version: str = "1.0.0"


class MemoryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    fingerprint: EpisodeFingerprint
    symbol: Symbol | None = None
    top_k: int = 5
    min_similarity: float = 0.0


class MemoryResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    record: EpisodeRecord
    similarity: float


class MemoryRecall(BaseModel):
    """The Layer 4 output payload — never mutates; references upstream
    diagnosis via `correlated_event_id`.
    """

    model_config = ConfigDict(frozen=True)
    analogs: list[MemoryResult] = Field(default_factory=list)
    sequence_match: list[str] = Field(default_factory=list)
    archive_size: int = 0
    written: bool = False
    correlated_event_id: str | None = None
    layer: LayerName = LayerName.MEMORY
