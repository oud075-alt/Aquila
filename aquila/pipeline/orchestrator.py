"""Cognitive orchestrator — runs the full DAG for one tick.

Pure function semantics: given (clock, context, bar, cached state in
layers), produces a deterministic dict of `LayerOutput`s. Errors in any
layer are caught and converted to `error_state` outputs so the rest of the
pipeline can continue and L8 can observe degraded visibility.
"""

from __future__ import annotations

import traceback
import uuid
from typing import Any

from aquila.core.base import LayerContext, LayerOutput
from aquila.core.clock import Clock, WallClock
from aquila.core.types import LayerName, Symbol
from aquila.deception import DeceptionIntelligenceLayer
from aquila.memory import EpisodicMemoryLayer
from aquila.meta import MetaCognitionLayer, MetaSignal
from aquila.observability import AuditLog, Telemetry, get_logger
from aquila.pathology import PathologyContradictionLayer
from aquila.pipeline.event_bus import EventBus
from aquila.pipeline.lifecycle import EventLifecycle, LifecyclePhase
from aquila.primitives import PrimitiveBar, PrimitiveMetricsLayer
from aquila.regime import RegimeMutationLayer
from aquila.safety import SafetyKernel
from aquila.structural import StructuralDiagnosisLayer
from aquila.temporal import TemporalHierarchyLayer

log = get_logger("orchestrator")


class CognitiveOrchestrator:
    def __init__(
        self,
        clock: Clock | None = None,
        bus: EventBus | None = None,
        safety: SafetyKernel | None = None,
        audit: AuditLog | None = None,
        telemetry: Telemetry | None = None,
        primitives: PrimitiveMetricsLayer | None = None,
        structural: StructuralDiagnosisLayer | None = None,
        pathology: PathologyContradictionLayer | None = None,
        memory: EpisodicMemoryLayer | None = None,
        temporal: TemporalHierarchyLayer | None = None,
        deception: DeceptionIntelligenceLayer | None = None,
        regime: RegimeMutationLayer | None = None,
        meta: MetaCognitionLayer | None = None,
    ) -> None:
        self.clock = clock or WallClock()
        self.bus = bus or EventBus()
        self.safety = safety or SafetyKernel()
        self.audit = audit or AuditLog()
        self.telemetry = telemetry or Telemetry()

        self.primitives = primitives or PrimitiveMetricsLayer()
        self.structural = structural or StructuralDiagnosisLayer()
        self.pathology = pathology or PathologyContradictionLayer()
        self.memory = memory or EpisodicMemoryLayer()
        self.temporal = temporal or TemporalHierarchyLayer()
        self.deception = deception or DeceptionIntelligenceLayer()
        self.regime = regime or RegimeMutationLayer()
        self.meta = meta or MetaCognitionLayer()

        self._last_meta_signal: dict[str, Any] = {}

    def _safe(self, layer, payload, ctx) -> LayerOutput:
        with self.telemetry.time(f"layer.{layer.layer_name.value}"):
            try:
                out = layer.process(payload, ctx)
                out = self.safety.enforce(out)
            except Exception as e:
                log.error("layer %s failed: %s", layer.layer_name.value, e)
                log.debug(traceback.format_exc())
                # Build a minimal error output so downstream sees degraded visibility
                # We instantiate an empty payload by re-using the layer's last
                # successful output type if available — fall back to a dict.
                from pydantic import BaseModel

                class _EmptyPayload(BaseModel):
                    error: str

                out = LayerOutput(
                    layer=layer.layer_name,
                    symbol=ctx.symbol,
                    correlation_id=ctx.correlation_id,
                    payload=_EmptyPayload(error=str(e)),
                    confidence=0.0,
                    visibility="degraded",
                    error_state=str(e),
                )
        self.bus.publish(out)
        self.audit.append(out)
        self.telemetry.incr(f"layer.{layer.layer_name.value}.emitted")
        return out

    def run_tick(
        self,
        symbol: Symbol,
        bar: PrimitiveBar,
        *,
        correlation_id: str | None = None,
        origin: str = "real",
    ) -> dict[LayerName, LayerOutput]:
        corr = correlation_id or str(uuid.uuid4())
        ctx = LayerContext(
            correlation_id=corr,
            symbol=symbol,
            origin=origin,  # type: ignore[arg-type]
            meta_signal=dict(self._last_meta_signal),
        )
        ctx = ctx.with_clock(self.clock.now)

        prim = self._safe(self.primitives, bar, ctx); ctx.record(prim)
        struct = self._safe(self.structural, prim.payload, ctx); ctx.record(struct)
        path = self._safe(self.pathology, struct.payload, ctx); ctx.record(path)

        mem = self._safe(self.memory, path.payload, ctx); ctx.record(mem)
        temp = self._safe(self.temporal, [], ctx); ctx.record(temp)
        decep = self._safe(self.deception, path.payload, ctx); ctx.record(decep)
        reg = self._safe(self.regime, path.payload, ctx); ctx.record(reg)

        meta = self._safe(self.meta, {}, ctx); ctx.record(meta)

        ms: MetaSignal = meta.payload.meta_signal  # type: ignore[assignment]
        self._last_meta_signal = ms.model_dump()

        return dict(ctx.upstream_outputs)

    def lifecycle(self, outputs: dict[LayerName, LayerOutput]) -> EventLifecycle:
        completed: list[LifecyclePhase] = []
        mapping = {
            LayerName.PRIMITIVES: LifecyclePhase.PRIMITIVES,
            LayerName.STRUCTURAL: LifecyclePhase.STRUCTURAL,
            LayerName.PATHOLOGY: LifecyclePhase.PATHOLOGY,
            LayerName.MEMORY: LifecyclePhase.MEMORY,
            LayerName.TEMPORAL: LifecyclePhase.TEMPORAL,
            LayerName.DECEPTION: LifecyclePhase.DECEPTION,
            LayerName.REGIME: LifecyclePhase.REGIME,
            LayerName.META: LifecyclePhase.META,
        }
        confs: dict[LayerName, float] = {}
        for ln, ph in mapping.items():
            if ln in outputs and outputs[ln].error_state is None:
                completed.append(ph)
                confs[ln] = outputs[ln].confidence
        completed.append(LifecyclePhase.DONE)
        corr = next(iter(outputs.values())).correlation_id if outputs else ""
        return EventLifecycle(correlation_id=corr, phases_completed=completed, layer_confidences=confs)
