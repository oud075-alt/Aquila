"""Common Pydantic v2 base for every MSPIS schema.

All schemas in core.schemas inherit from MSPISSchema. This enforces:

    - immutability (frozen)
    - extra-field rejection
    - strict type coercion
    - mandatory schema_version / timestamp / timeframe / source / confidence

These five fields are required by Phase 0A.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.schemas.enums import SourceMode, Timeframe

SCHEMA_VERSION: str = "0.1.0"

ConfidenceFloat = Annotated[float, Field(ge=0.0, le=1.0)]
UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]


class MSPISSchema(BaseModel):
    """Frozen, strict, extra-forbid Pydantic base for all MSPIS state objects."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        arbitrary_types_allowed=False,
        validate_default=True,
        ser_json_timedelta="iso8601",
    )

    schema_version: str = Field(default=SCHEMA_VERSION)
    timestamp: datetime
    timeframe: Timeframe
    source: SourceMode
    confidence: ConfidenceFloat

    @field_validator("timestamp")
    @classmethod
    def _require_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware UTC")
        if v.utcoffset() != UTC.utcoffset(v):
            return v.astimezone(UTC)
        return v

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"schema_version must be SemVer, got {v!r}")
        return v
