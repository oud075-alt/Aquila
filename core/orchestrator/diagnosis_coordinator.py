"""Diagnosis coordinator — top-level orchestrator facade.

Callers interact with `DiagnosisCoordinator`. Brain-layer hooks
(decision_engine, risk_intelligence, context_fusion, strategy_router,
adaptive_learning) are injected at construction. If absent, deterministic
Phase 0 defaults are used.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from core.ingestion.base_adapter import BaseAdapter, IngestionEvent
from core.orchestrator.context_manager import ContextManager
from core.orchestrator.pipeline_executor import (
    ContextHook,
    DecisionHook,
    PipelineExecutor,
    RiskHook,
    RouterHook,
)
from core.orchestrator.state_bus import StateBus, StateKey
from core.schemas.diagnosis_envelope import DiagnosisEnvelope
from core.schemas.enums import SourceMode, Timeframe
from core.schemas.market_state import DEFAULT_SYMBOL, MarketState


class AdaptiveLearningHook(Protocol):
    """Phase 5 sink protocol. Any object with `.observe(envelope, market_state)` qualifies."""

    async def observe(
        self,
        *,
        envelope: DiagnosisEnvelope,
        market_state: MarketState,
    ) -> None:  # pragma: no cover - protocol
        ...


class DiagnosisCoordinator:
    """Single authoritative entry point for producing DiagnosisEnvelopes."""

    def __init__(
        self,
        *,
        symbol: str = DEFAULT_SYMBOL,
        source: SourceMode = SourceMode.REPLAY,
        timeframes: tuple[Timeframe, ...] = (Timeframe.ONE_MIN,),
        tail_length: int = 256,
        decision_hook: DecisionHook | None = None,
        risk_hook: RiskHook | None = None,
        context_fusion_hook: ContextHook | None = None,
        strategy_router_hook: RouterHook | None = None,
        adaptive_learning_hook: AdaptiveLearningHook | None = None,
    ) -> None:
        self.symbol = symbol.upper()
        self.source = source
        self.context_manager = ContextManager(
            symbol=self.symbol, source=source, timeframes=timeframes, tail_length=tail_length
        )
        self.state_bus = StateBus()
        self.executor = PipelineExecutor(
            context_manager=self.context_manager,
            decision_hook=decision_hook,
            risk_hook=risk_hook,
            context_fusion_hook=context_fusion_hook,
            strategy_router_hook=strategy_router_hook,
        )
        self.adaptive_learning = adaptive_learning_hook

    async def diagnose_event(self, event: IngestionEvent) -> DiagnosisEnvelope:
        """Push one ingestion event through the full DAG."""
        stream = self.context_manager.stream(timeframe=event.bar.timeframe)
        market_state = stream.pipeline.push(event)
        stream.market_state = market_state

        envelope = await self.executor.diagnose(market_state)
        stream.pathology = envelope.pathology
        stream.regime = envelope.regime
        stream.last_update = envelope.timestamp

        await self.state_bus.publish(
            StateKey(symbol=self.symbol, timeframe=event.bar.timeframe, kind="diagnosis"),
            envelope,
        )

        if self.adaptive_learning is not None:
            try:
                await self.adaptive_learning.observe(envelope=envelope, market_state=market_state)
            except Exception:  # pragma: no cover - learning must never crash diagnosis
                pass

        return envelope

    async def diagnose_stream(self, adapter: BaseAdapter) -> AsyncIterator[DiagnosisEnvelope]:
        """Consume an ingestion stream and yield DiagnosisEnvelopes."""
        async for event in adapter.stream():
            yield await self.diagnose_event(event)
