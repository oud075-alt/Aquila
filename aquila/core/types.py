"""Foundational scalar / domain types shared across all layers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, NewType

from pydantic import Field

Symbol = NewType("Symbol", str)
Timestamp = NewType("Timestamp", datetime)

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]


class Severity(str, Enum):
    """Generic severity scale used by pathology / deception / regime layers."""

    NIL = "nil"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class LayerName(str, Enum):
    """Canonical layer identifiers — enforced across schemas, routes, replay."""

    PRIMITIVES = "primitives"
    STRUCTURAL = "structural"
    PATHOLOGY = "pathology"
    MEMORY = "memory"
    TEMPORAL = "temporal"
    DECEPTION = "deception"
    REGIME = "regime"
    META = "meta"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
