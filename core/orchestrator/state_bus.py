"""State bus — typed in-memory current-state cache used across the orchestrator.

This is not a pubsub. It is a thread-safe (asyncio-lock-protected) typed
key→value store keyed by `(symbol, timeframe, kind)`. Engines write the
latest state; readers always see the most recent value.

Conflicting state objects are NOT permitted — writing a new value of a
given key overwrites the prior one and bumps `version`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from core.schemas.enums import Timeframe


@dataclass(frozen=True, slots=True)
class StateKey:
    symbol: str
    timeframe: Timeframe
    kind: str


@dataclass(frozen=True, slots=True)
class StateEnvelope:
    key: StateKey
    value: Any
    version: int


@dataclass(slots=True)
class _Slot:
    value: Any = None
    version: int = 0
    has_value: bool = False


class StateBus:
    """Async-safe latest-value cache."""

    def __init__(self) -> None:
        self._slots: dict[StateKey, _Slot] = {}
        self._lock = asyncio.Lock()
        self._listeners: dict[StateKey, list[asyncio.Event]] = {}
        self._metrics: dict[str, int] = field(default_factory=dict) if False else {}

    async def publish(self, key: StateKey, value: Any) -> StateEnvelope:
        async with self._lock:
            slot = self._slots.setdefault(key, _Slot())
            slot.value = value
            slot.version += 1
            slot.has_value = True
            self._metrics[f"publish:{key.kind}"] = self._metrics.get(f"publish:{key.kind}", 0) + 1
            envelope = StateEnvelope(key=key, value=value, version=slot.version)
            for ev in self._listeners.get(key, []):
                ev.set()
        return envelope

    async def get(self, key: StateKey) -> StateEnvelope | None:
        async with self._lock:
            slot = self._slots.get(key)
            if slot is None or not slot.has_value:
                return None
            return StateEnvelope(key=key, value=slot.value, version=slot.version)

    async def wait_for(self, key: StateKey, *, timeout: float | None = None) -> StateEnvelope:
        event = asyncio.Event()
        async with self._lock:
            self._listeners.setdefault(key, []).append(event)
            current = self._slots.get(key)
            if current and current.has_value:
                event.set()

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        finally:
            async with self._lock:
                listeners = self._listeners.get(key, [])
                if event in listeners:
                    listeners.remove(event)

        envelope = await self.get(key)
        if envelope is None:
            raise RuntimeError(f"state_bus: no value for {key} after wait_for completed")
        return envelope

    @property
    def metrics(self) -> dict[str, int]:
        return dict(self._metrics)
