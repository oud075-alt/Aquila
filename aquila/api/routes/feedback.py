"""Analyst feedback intake — closes audit gap #67.

CRITICAL: this endpoint is read-only with respect to cognition state. It
stores researcher annotations alongside outputs but NEVER mutates layers'
internal state. This preserves the "no self-modifying code" invariant.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from aquila.core.types import utcnow

router = APIRouter(prefix="/feedback", tags=["feedback"])


class Annotation(BaseModel):
    correlation_id: str
    note: str
    submitted_at: datetime = Field(default_factory=utcnow)


_ANNOTATIONS: list[Annotation] = []


@router.post("/annotate")
def annotate(a: Annotation) -> dict:
    _ANNOTATIONS.append(a)
    return {"stored": True, "count": len(_ANNOTATIONS)}


@router.get("/list")
def list_annotations() -> dict:
    return {"annotations": [a.model_dump() for a in _ANNOTATIONS]}
