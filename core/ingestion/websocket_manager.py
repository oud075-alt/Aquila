"""Websocket connection manager — reconnect, heartbeat, backoff.

Live-mode utility. Phase 0 does not depend on this for replay determinism.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import websockets
from websockets.exceptions import ConnectionClosed


@dataclass(frozen=True, slots=True)
class WSMessage:
    payload: dict[str, object]
    received_at: datetime


class WebsocketManager:
    """Reconnecting websocket client with heartbeat and exponential backoff.

    Yields parsed JSON payloads as `WSMessage`. Reconnects forever with
    bounded exponential backoff. Heartbeat warnings emit via the optional
    `on_stale` callback.
    """

    def __init__(
        self,
        url: str,
        *,
        heartbeat_seconds: float = 30.0,
        max_backoff_seconds: float = 32.0,
        on_stale: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        self.url = url
        self.heartbeat_seconds = heartbeat_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.on_stale = on_stale
        self._last_message_at: datetime | None = None

    @property
    def last_message_at(self) -> datetime | None:
        return self._last_message_at

    async def stream(self) -> AsyncIterator[WSMessage]:
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(self.url, ping_interval=20) as ws:
                    backoff = 1.0
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    try:
                        async for raw in ws:
                            now = datetime.now(tz=UTC)
                            self._last_message_at = now
                            try:
                                payload = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            if not isinstance(payload, dict):
                                continue
                            yield WSMessage(payload=payload, received_at=now)
                    finally:
                        heartbeat_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await heartbeat_task
            except (ConnectionClosed, OSError):
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, self.max_backoff_seconds)

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            if self._last_message_at is None:
                continue
            lag = (datetime.now(tz=UTC) - self._last_message_at).total_seconds()
            if lag > self.heartbeat_seconds and self.on_stale is not None:
                await self.on_stale(lag)
