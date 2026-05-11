"""Base classes for cognitive layers, layer I/O, and event identity.

All layers MUST inherit `CognitiveLayer`. All layer outputs MUST be frozen
Pydantic models, fulfilling the immutability requirement of the expanded
prompt's "bounded cognitive contexts" rules.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from aquila.core.types import Confidence, LayerName, Symbol, utcnow

SCHEMA_VERSION = "1.0.0"

T_IN = TypeVar("T_IN", bound=BaseModel)
T_OUT = TypeVar("T_OUT", bound=BaseModel)


class EventRef(BaseModel):
    """Citation pointer to an upstream event/output. Required for "evidence

    citation per conclusion" (audit gap #54).
    """

    model_config = ConfigDict(frozen=True)

    event_id: str
    layer: LayerName
    timestamp: datetime


class LayerInput(BaseModel):
    """Generic input wrapper carried through the pipeline DAG."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Symbol
    timestamp: datetime
    upstream: dict[str, Any] = Field(default_factory=dict)
    meta_signal: dict[str, Any] = Field(default_factory=dict)


VisibilityState = Literal["full", "partial", "degraded", "blind"]
Origin = Literal["real", "synthetic", "replay"]


class LayerOutput(BaseModel, Generic[T_OUT]):
    """Immutable output emitted by every cognitive layer.

    Frozen by design — bounded-context rule from the expanded prompt:
    "no direct cross-layer mutation of state". Downstream layers MUST treat
    upstream outputs as read-only snapshots.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = SCHEMA_VERSION
    layer: LayerName
    symbol: Symbol
    timestamp: datetime = Field(default_factory=utcnow)
    correlation_id: str

    payload: T_OUT
    confidence: Confidence = 0.0
    visibility: VisibilityState = "full"
    origin: Origin = "real"
    ttl_seconds: int | None = None
    evidence: list[EventRef] = Field(default_factory=list)
    error_state: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    def as_ref(self) -> EventRef:
        return EventRef(event_id=self.event_id, layer=self.layer, timestamp=self.timestamp)


class CognitiveLayer(ABC, Generic[T_IN, T_OUT]):
    """Base class for every cognitive layer.

    Implementations MUST be pure functions of `(input, context)`. They MUST
    NOT mutate shared state. State persistence is delegated to dedicated
    stores (memory, event log) accessed via injected interfaces.

    Bounded-context rule: layers communicate ONLY through `LayerOutput`
    instances on the event bus or via the orchestrator's per-cycle context.
    """

    layer_name: LayerName

    def __init__(self, *, schema_version: str = SCHEMA_VERSION) -> None:
        self.schema_version = schema_version

    @abstractmethod
    def process(self, payload: T_IN, ctx: "LayerContext") -> LayerOutput[T_OUT]:
        """Execute the layer's cognition on `payload`. Pure function."""
        raise NotImplementedError

    def wrap(
        self,
        *,
        payload: T_OUT,
        ctx: "LayerContext",
        confidence: float = 0.0,
        visibility: VisibilityState = "full",
        evidence: list[EventRef] | None = None,
        ttl_seconds: int | None = None,
        error_state: str | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> LayerOutput[T_OUT]:
        """Helper for subclasses to produce a `LayerOutput` consistently."""
        return LayerOutput[T_OUT](
            layer=self.layer_name,
            symbol=ctx.symbol,
            timestamp=ctx.now(),
            correlation_id=ctx.correlation_id,
            payload=payload,
            confidence=confidence,
            visibility=visibility,
            origin=ctx.origin,
            ttl_seconds=ttl_seconds,
            evidence=evidence or [],
            error_state=error_state,
            diagnostics=diagnostics or {},
            schema_version=self.schema_version,
        )


class LayerContext(BaseModel):
    """Per-cycle execution context. Carries clock, RNG seed, origin, and
    upstream outputs accumulated within the current pipeline pass.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    correlation_id: str
    symbol: Symbol
    origin: Origin = "real"
    seed: int = 0
    upstream_outputs: dict[LayerName, LayerOutput] = Field(default_factory=dict)
    meta_signal: dict[str, Any] = Field(default_factory=dict)
    _clock_callable: Any = None

    def now(self) -> datetime:
        if self._clock_callable is not None:
            return self._clock_callable()
        return utcnow()

    def with_clock(self, clock_fn) -> "LayerContext":
        new = self.model_copy()
        new._clock_callable = clock_fn
        return new

    def record(self, output: LayerOutput) -> None:
        """Record an output for downstream layers within the same cycle.

        This is the ONLY mutation point per cycle; the dict is fresh per
        cycle and never shared across cycles.
        """
        self.upstream_outputs[output.layer] = output
